import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "tmp" / "test_guest_checkout_idempotency.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

from source.db.models import Base, Category, IdempotencyRecord, Order, Product, ProductVariant
from source.db.session import SessionLocal, engine
from source.routes.orders_r import create_guest_checkout_order
from source.schemas.orders_s import PublicGuestCheckoutRequest
from source.services.idempotency_s import prune_expired_records


class GuestCheckoutIdempotencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        if DB_PATH.exists():
            DB_PATH.unlink()
        Base.metadata.create_all(bind=engine)

    @classmethod
    def tearDownClass(cls) -> None:
        engine.dispose()
        if DB_PATH.exists():
            DB_PATH.unlink()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self._seed_catalog()

    def _request(self, *, ip: str = "127.0.0.1") -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/checkout/guest",
            "headers": [],
            "client": (ip, 12345),
        }
        return Request(scope)

    def _payload_model(self, *, email: str = "guest@example.com", qty: int = 1) -> PublicGuestCheckoutRequest:
        return PublicGuestCheckoutRequest.model_validate(
            {
                "customer": {
                    "email": email,
                    "first_name": "Guest",
                    "last_name": "Buyer",
                    "phone": "1122334455",
                },
                "items": [{"variant_id": 1, "quantity": qty}],
                "website": None,
            }
        )

    def _seed_catalog(self) -> None:
        db = SessionLocal()
        try:
            category = Category(name="cat-demo")
            db.add(category)
            db.flush()

            product = Product(name="Prod demo", description=None, category_id=category.id)
            db.add(product)
            db.flush()

            variant = ProductVariant(
                product_id=product.id,
                sku="GUEST-SKU-1",
                size="M",
                color="Blue",
                price=10000,
                stock=20,
                is_active=True,
            )
            db.add(variant)
            db.commit()
        finally:
            db.close()

    def _call_guest(
        self,
        *,
        payload: PublicGuestCheckoutRequest,
        key: str,
        ip: str = "127.0.0.1",
        bypass_anti_abuse: bool = True,
    ) -> dict:
        db = SessionLocal()
        try:
            if bypass_anti_abuse:
                with patch("source.routes.orders_r.enforce_public_guest_checkout_limits", return_value=None):
                    response = create_guest_checkout_order(
                        payload=payload,
                        request=self._request(ip=ip),
                        idempotency_key=key,
                        db=db,
                    )
            else:
                response = create_guest_checkout_order(
                    payload=payload,
                    request=self._request(ip=ip),
                    idempotency_key=key,
                    db=db,
                )
            db.commit()
            return response
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def test_guest_checkout_first_request_creates_order(self) -> None:
        response = self._call_guest(
            payload=self._payload_model(),
            key="guest-key-1",
        )
        self.assertIn("data", response)
        self.assertIn("order", response["data"])

        db = SessionLocal()
        try:
            orders = db.query(Order).all()
            self.assertEqual(len(orders), 1)
        finally:
            db.close()

    def test_guest_checkout_same_key_same_scope_same_payload_replays_201(self) -> None:
        payload = self._payload_model(email="same@example.com")

        first = self._call_guest(payload=payload, key="guest-replay-key")
        second = self._call_guest(payload=payload, key="guest-replay-key")

        self.assertEqual(first["data"]["order"]["id"], second["data"]["order"]["id"])

        db = SessionLocal()
        try:
            orders = db.query(Order).all()
            self.assertEqual(len(orders), 1)
        finally:
            db.close()

    def test_guest_checkout_same_key_same_scope_different_payload_returns_409(self) -> None:
        first_payload = self._payload_model(email="conflict@example.com", qty=1)
        second_payload = self._payload_model(email="conflict@example.com", qty=2)

        first = self._call_guest(payload=first_payload, key="guest-conflict-key")
        self.assertIn("data", first)

        with self.assertRaises(HTTPException) as ctx:
            self._call_guest(payload=second_payload, key="guest-conflict-key")
        self.assertEqual(ctx.exception.status_code, 409)

        db = SessionLocal()
        try:
            orders = db.query(Order).all()
            self.assertEqual(len(orders), 1)
        finally:
            db.close()

    def test_guest_checkout_same_key_different_email_allows_new_order(self) -> None:
        first = self._call_guest(
            payload=self._payload_model(email="a@example.com"),
            key="guest-same-key",
        )
        second = self._call_guest(
            payload=self._payload_model(email="b@example.com"),
            key="guest-same-key",
        )
        self.assertNotEqual(first["data"]["order"]["id"], second["data"]["order"]["id"])

        db = SessionLocal()
        try:
            orders = db.query(Order).all()
            self.assertEqual(len(orders), 2)
        finally:
            db.close()

    def test_guest_checkout_missing_idempotency_key_fails_validation(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            self._call_guest(
                payload=self._payload_model(),
                key="",
            )
        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "idempotency_key is required")

    def test_guest_checkout_concurrent_requests_same_key_create_single_order(self) -> None:
        payload = self._payload_model(email="concurrent@example.com")

        def _call() -> tuple[str, int | None]:
            try:
                response = self._call_guest(
                    payload=payload,
                    key="guest-concurrent-key",
                )
                return "ok", int(response["data"]["order"]["id"])
            except HTTPException as exc:
                return f"http_{exc.status_code}", None

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: _call(), range(2)))

        statuses = [status for status, _ in results]
        self.assertIn("ok", statuses)
        self.assertTrue(
            all(status in {"ok", "http_409"} for status in statuses),
            f"unexpected statuses: {statuses}",
        )

        db = SessionLocal()
        try:
            orders = db.query(Order).all()
            self.assertEqual(len(orders), 1)
        finally:
            db.close()

    def test_idempotency_record_expiration_pruning(self) -> None:
        db = SessionLocal()
        try:
            db.add(
                IdempotencyRecord(
                    scope="checkout_guest:expired@example.com",
                    idempotency_key="expired-key",
                    request_hash="h",
                    response_payload='{"ok":true}',
                    status="completed",
                    created_at=datetime.now(UTC) - timedelta(days=2),
                    expires_at=datetime.now(UTC) - timedelta(days=1),
                )
            )
            db.add(
                IdempotencyRecord(
                    scope="checkout_guest:active@example.com",
                    idempotency_key="active-key",
                    request_hash="h2",
                    response_payload='{"ok":true}',
                    status="completed",
                    created_at=datetime.now(UTC),
                    expires_at=datetime.now(UTC) + timedelta(hours=6),
                )
            )
            db.commit()

            deleted = prune_expired_records(now=datetime.now(UTC), db=db, limit=200)
            self.assertEqual(deleted, 1)

            remaining = (
                db.query(IdempotencyRecord)
                .order_by(IdempotencyRecord.id.asc())
                .all()
            )
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0].idempotency_key, "active-key")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

