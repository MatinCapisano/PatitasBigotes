import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import Base, Order, Payment, PaymentIncident, User
from source.services.refund_s import (
    create_mercadopago_refund,
    resolve_payment_incident_no_refund,
)


class PaymentIncidentsRefundsTests(unittest.TestCase):
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

    def _seed_incident(self) -> tuple[int, int]:
        session = self.TestSession()
        try:
            customer = User(
                first_name="Jane",
                last_name="Customer",
                email=f"customer-{datetime.now(UTC).timestamp()}@example.com",
                password_hash="!",
                has_account=False,
                is_admin=False,
            )
            admin = User(
                first_name="Admin",
                last_name="User",
                email=f"admin-{datetime.now(UTC).timestamp()}@example.com",
                password_hash="!",
                has_account=True,
                is_admin=True,
            )
            session.add_all([customer, admin])
            session.flush()

            order = Order(
                user_id=int(customer.id),
                status="paid",
                currency="ARS",
                subtotal=10000,
                discount_total=0,
                total_amount=10000,
                pricing_frozen=True,
                submitted_at=datetime.now(UTC),
                paid_at=datetime.now(UTC),
            )
            session.add(order)
            session.flush()

            payment = Payment(
                order_id=int(order.id),
                method="mercadopago",
                status="paid",
                amount=10000,
                currency="ARS",
                idempotency_key=f"idemp-paid-{datetime.now(UTC).timestamp()}",
                external_ref=f"mp-order-{order.id}-pay-2",
                provider_status="approved",
                provider_payload='{"reconciliation":{"provider_payment_id":"123456"}}',
                receipt_url=None,
                expires_at=None,
                paid_at=datetime.now(UTC),
            )
            session.add(payment)
            session.flush()

            incident = PaymentIncident(
                order_id=int(order.id),
                payment_id=int(payment.id),
                type="late_paid_duplicate",
                status="pending_review",
                reason="late approval",
            )
            session.add(incident)
            session.commit()
            return int(incident.id), int(admin.id)
        finally:
            session.close()

    def test_resolve_refund_success(self) -> None:
        incident_id, admin_user_id = self._seed_incident()
        session = self.TestSession()
        try:
            with patch(
                "source.services.refund_s.create_refund",
                return_value={"id": 9001, "status": "approved"},
            ):
                result = create_mercadopago_refund(
                    incident_id=incident_id,
                    amount=None,
                    admin_user_id=admin_user_id,
                    reason="cliente ya pago en local",
                    db=session,
                )
            session.commit()
        finally:
            session.close()

        self.assertEqual(result["incident"]["status"], "resolved_refunded")
        self.assertEqual(result["refund"]["status"], "approved")
        self.assertEqual(result["refund"]["provider_refund_id"], "9001")

    def test_resolve_refund_is_idempotent_for_same_incident(self) -> None:
        incident_id, admin_user_id = self._seed_incident()
        session = self.TestSession()
        try:
            with patch(
                "source.services.refund_s.create_refund",
                return_value={"id": 9010, "status": "approved"},
            ):
                first = create_mercadopago_refund(
                    incident_id=incident_id,
                    amount=10000,
                    admin_user_id=admin_user_id,
                    reason="cliente ya pago en local",
                    db=session,
                )
                second = create_mercadopago_refund(
                    incident_id=incident_id,
                    amount=10000,
                    admin_user_id=admin_user_id,
                    reason="cliente ya pago en local",
                    db=session,
                )
            session.commit()
        finally:
            session.close()

        self.assertEqual(first["refund"]["id"], second["refund"]["id"])
        self.assertEqual(second["incident"]["status"], "resolved_refunded")

    def test_resolve_incident_no_refund_requires_reason(self) -> None:
        incident_id, admin_user_id = self._seed_incident()
        session = self.TestSession()
        try:
            with self.assertRaises(ValueError):
                resolve_payment_incident_no_refund(
                    incident_id=incident_id,
                    admin_user_id=admin_user_id,
                    reason="",
                    db=session,
                )
            updated = resolve_payment_incident_no_refund(
                incident_id=incident_id,
                admin_user_id=admin_user_id,
                reason="caso validado y no corresponde devolver",
                db=session,
            )
            session.commit()
        finally:
            session.close()

        self.assertEqual(updated["status"], "resolved_no_refund")
        self.assertEqual(updated["resolved_by_user_id"], admin_user_id)


if __name__ == "__main__":
    unittest.main()
