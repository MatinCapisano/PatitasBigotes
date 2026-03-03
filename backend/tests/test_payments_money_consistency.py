import sys
import unittest
from datetime import datetime, timedelta
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
    Product,
    ProductVariant,
    StockReservation,
    User,
)
from source.services.payment_s import (
    apply_mercadopago_normalized_state,
    create_payment_for_order,
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
                email=f"jane-{datetime.utcnow().timestamp()}@example.com",
                password_hash="!",
                has_account=False,
                is_admin=False,
            )
            category = Category(name=f"cat-{datetime.utcnow().timestamp()}")
            session.add_all([user, category])
            session.flush()

            product = Product(name="Test Product", description=None, category_id=category.id)
            session.add(product)
            session.flush()

            variant = ProductVariant(
                product_id=product.id,
                sku=f"SKU-{datetime.utcnow().timestamp()}",
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
                    expires_at=datetime.utcnow() + timedelta(hours=1),
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
                idempotency_key=f"idemp-{datetime.utcnow().timestamp()}",
                currency="ARS",
            )
            session.commit()
        finally:
            session.close()
        self.assertEqual(payment["amount"], 10000)

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
                idempotency_key=f"idemp-mp-{datetime.utcnow().timestamp()}",
                external_ref=f"mp-order-{order_id}-pay-1",
                provider_status="preference_created",
                provider_payload=None,
                receipt_url=None,
                expires_at=datetime.utcnow() + timedelta(hours=1),
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


if __name__ == "__main__":
    unittest.main()
