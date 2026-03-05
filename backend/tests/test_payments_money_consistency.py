import sys
import unittest
from datetime import datetime, timedelta, UTC
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import (
    Base,
    Category,
    Order,
    OrderItem,
    Payment,
    PaymentIncident,
    Product,
    ProductVariant,
    StockReservation,
    User,
)
from source.services.payment_s import (
    apply_mercadopago_normalized_state,
    create_payment_for_order,
    create_retry_payment_for_order,
    find_payment_for_mercadopago_event,
    submit_bank_transfer_receipt,
)


class PaymentsMoneyConsistencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.engine = create_engine("sqlite:///:memory:")
        cls.TestSession = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=cls.engine,
        )
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.engine.dispose()

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def _seed_submitted_order_with_reservation(self) -> tuple[int, int]:
        session = self.TestSession()
        try:
            user = User(
                first_name="Jane",
                last_name="Doe",
                email=f"jane-{datetime.now(UTC).timestamp()}@example.com",
                password_hash="!",
                has_account=False,
                is_admin=False,
            )
            category = Category(name=f"cat-{datetime.now(UTC).timestamp()}")
            session.add_all([user, category])
            session.flush()

            product = Product(name="Test Product", description=None, category_id=category.id)
            session.add(product)
            session.flush()

            variant = ProductVariant(
                product_id=product.id,
                sku=f"SKU-{datetime.now(UTC).timestamp()}",
                size="M",
                color="Blue",
                price=10000,
                stock=5,
                is_active=True,
            )
            session.add(variant)
            session.flush()

            order = Order(
                user_id=user.id,
                status="submitted",
                currency="ARS",
                subtotal=10000,
                discount_total=0,
                total_amount=10000,
                pricing_frozen=True,
            )
            session.add(order)
            session.flush()

            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                variant_id=variant.id,
                quantity=1,
                unit_price=10000,
                discount_id=None,
                discount_amount=0,
                final_unit_price=10000,
                line_total=10000,
            )
            session.add(item)
            session.flush()

            session.add(
                StockReservation(
                    order_id=order.id,
                    order_item_id=item.id,
                    variant_id=variant.id,
                    quantity=1,
                    status="active",
                    expires_at=datetime.now(UTC) + timedelta(hours=1),
                )
            )
            session.commit()
            return int(order.id), int(user.id)
        finally:
            session.close()

    def test_create_payment_uses_exact_order_total(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            payment = create_payment_for_order(
                order_id=order_id,
                method="bank_transfer",
                db=session,
                user_id=user_id,
                idempotency_key=f"idemp-{datetime.now(UTC).timestamp()}",
                currency="ARS",
            )
            session.commit()
        finally:
            session.close()
        self.assertEqual(payment["amount"], 10000)
        self.assertIn("provider_payload_data", payment)
        self.assertIsInstance(payment["provider_payload_data"], dict)

    def test_create_payment_rejects_non_ars_currency(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            with self.assertRaises(ValueError) as ctx:
                create_payment_for_order(
                    order_id=order_id,
                    method="bank_transfer",
                    db=session,
                    user_id=user_id,
                    idempotency_key=f"idemp-usd-{datetime.now(UTC).timestamp()}",
                    currency="USD",
                )
            self.assertEqual(str(ctx.exception), "only ARS currency is supported")
        finally:
            session.close()

    def test_webhook_amount_mismatch_raises(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            payment = Payment(
                order_id=order_id,
                method="mercadopago",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-mp-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-1",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(payment)
            session.flush()
            with self.assertRaises(ValueError):
                apply_mercadopago_normalized_state(
                    payment_id=int(payment.id),
                    normalized_state={
                        "provider_status": "approved",
                        "internal_status": "paid",
                        "external_reference": payment.external_ref,
                        "amount": 10001,
                        "currency": "ARS",
                        "provider_payment_id": "123",
                    },
                    db=session,
                )
        finally:
            session.close()

    def test_webhook_cancelled_payment_does_not_cancel_order(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            payment = Payment(
                order_id=order_id,
                method="mercadopago",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-mp-cancel-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-1",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(payment)
            session.flush()

            updated = apply_mercadopago_normalized_state(
                payment_id=int(payment.id),
                normalized_state={
                    "provider_status": "cancelled",
                    "internal_status": "cancelled",
                    "external_reference": payment.external_ref,
                    "amount": 10000,
                    "currency": "ARS",
                    "provider_payment_id": "321",
                },
                db=session,
            )

            order = session.query(Order).filter(Order.id == order_id).first()
            reservation = (
                session.query(StockReservation)
                .filter(
                    StockReservation.order_id == order_id,
                    StockReservation.status == "active",
                )
                .first()
            )
        finally:
            session.close()

        self.assertEqual(updated["status"], "cancelled")
        self.assertIsNotNone(order)
        self.assertEqual(order.status, "submitted")
        self.assertIsNotNone(reservation)

    def test_webhook_paid_on_cancelled_order_creates_incident_and_keeps_order_cancelled(self) -> None:
        order_id, _ = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            assert order is not None
            order.status = "cancelled"
            order.cancelled_at = datetime.now(UTC)

            payment = Payment(
                order_id=order_id,
                method="mercadopago",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-mp-late-cancel-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-late-cancel",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(payment)
            session.flush()

            updated = apply_mercadopago_normalized_state(
                payment_id=int(payment.id),
                normalized_state={
                    "provider_status": "approved",
                    "internal_status": "paid",
                    "external_reference": payment.external_ref,
                    "amount": 10000,
                    "currency": "ARS",
                    "provider_payment_id": "444",
                },
                db=session,
            )
            incidents = (
                session.query(PaymentIncident)
                .filter(PaymentIncident.payment_id == int(payment.id))
                .all()
            )
        finally:
            session.close()

        self.assertEqual(updated["status"], "paid")
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(len(incidents), 1)
        self.assertEqual(incidents[0].status, "pending_review")

    def test_webhook_paid_on_already_paid_order_creates_duplicate_incident(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            order = session.query(Order).filter(Order.id == order_id).first()
            assert order is not None
            existing_paid = Payment(
                order_id=order_id,
                method="cash",
                status="paid",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-paid-existing-{datetime.now(UTC).timestamp()}",
                external_ref=f"cash-ref-{order_id}",
                provider_status="manual_confirmed",
                provider_payload=None,
                receipt_url=None,
                expires_at=None,
                paid_at=datetime.now(UTC),
            )
            session.add(existing_paid)
            order.status = "paid"
            order.paid_at = datetime.now(UTC)

            late_payment = Payment(
                order_id=order_id,
                method="mercadopago",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-late-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-late",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(late_payment)
            session.flush()

            updated = apply_mercadopago_normalized_state(
                payment_id=int(late_payment.id),
                normalized_state={
                    "provider_status": "approved",
                    "internal_status": "paid",
                    "external_reference": late_payment.external_ref,
                    "amount": 10000,
                    "currency": "ARS",
                    "provider_payment_id": "555",
                },
                db=session,
            )
            incidents = (
                session.query(PaymentIncident)
                .filter(PaymentIncident.payment_id == int(late_payment.id))
                .all()
            )
            self.assertEqual(updated["status"], "paid")
            self.assertEqual(order.status, "paid")
            self.assertEqual(len(incidents), 1)
            self.assertEqual(incidents[0].status, "pending_review")
        finally:
            session.close()

    def test_retry_payment_creates_new_attempt_after_cancelled(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            cancelled = Payment(
                order_id=order_id,
                method="bank_transfer",
                status="cancelled",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-bt-cancelled-{datetime.now(UTC).timestamp()}",
                external_ref=f"bt-order-{order_id}-pay-9",
                provider_status="cancelled",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(cancelled)
            session.flush()
            cancelled_id = int(cancelled.id)

            retried = create_retry_payment_for_order(
                order_id=order_id,
                method="bank_transfer",
                db=session,
                user_id=user_id,
                currency="ARS",
                expires_in_minutes=60,
            )
            session.commit()
        finally:
            session.close()

        self.assertNotEqual(int(retried["id"]), cancelled_id)
        self.assertEqual(retried["status"], "pending")
        self.assertEqual(retried["method"], "bank_transfer")

    def test_retry_payment_requires_retryable_latest_status(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            pending = Payment(
                order_id=order_id,
                method="bank_transfer",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-bt-pending-{datetime.now(UTC).timestamp()}",
                external_ref=None,
                provider_status="pending",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(pending)
            session.flush()

            with self.assertRaises(ValueError) as ctx:
                create_retry_payment_for_order(
                    order_id=order_id,
                    method="bank_transfer",
                    db=session,
                    user_id=user_id,
                    currency="ARS",
                    expires_in_minutes=60,
                )
            self.assertEqual(str(ctx.exception), "latest payment attempt is not retryable")
        finally:
            session.close()

    def test_find_payment_by_preference_id_uses_dedicated_column(self) -> None:
        order_id, _ = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            payment = Payment(
                order_id=order_id,
                method="mercadopago",
                status="pending",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-pref-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-pref",
                preference_id=f"pref-{order_id}",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
                paid_at=None,
            )
            session.add(payment)
            session.commit()

            found = find_payment_for_mercadopago_event(
                preference_id=f"pref-{order_id}",
                external_ref=None,
                db=session,
            )
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found["id"], int(payment.id))
        finally:
            session.close()

    def test_submit_bank_transfer_receipt_updates_payment(self) -> None:
        order_id, user_id = self._seed_submitted_order_with_reservation()
        session = self.TestSession()
        try:
            payment = create_payment_for_order(
                order_id=order_id,
                method="bank_transfer",
                db=session,
                user_id=user_id,
                idempotency_key=f"idemp-receipt-{datetime.now(UTC).timestamp()}",
                currency="ARS",
            )
            updated = submit_bank_transfer_receipt(
                order_id=order_id,
                payment_id=int(payment["id"]),
                user_id=user_id,
                receipt_url="https://example.com/receipt-1.jpg",
                db=session,
            )
            session.commit()
        finally:
            session.close()

        self.assertEqual(updated["receipt_url"], "https://example.com/receipt-1.jpg")
        payload_data = updated.get("provider_payload_data") or {}
        self.assertIn("receipt", payload_data)
        self.assertEqual(payload_data["receipt"]["url"], "https://example.com/receipt-1.jpg")


if __name__ == "__main__":
    unittest.main()

