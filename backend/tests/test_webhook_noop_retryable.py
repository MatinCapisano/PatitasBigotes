import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import Base, WebhookEvent
from source.services.mercadopago_client import (
    WebhookNoOpError,
    resolver_evento_webhook_mercadopago,
)


class WebhookNoOpRetryableTests(unittest.TestCase):
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

    def test_payment_not_found_noop_marks_event_failed(self) -> None:
        session = self.TestSession()
        try:
            payload = {"type": "payment", "data": {"id": "123"}, "id": "evt-1"}
            with patch(
                "source.services.mercadopago_client.is_mercadopago_signature_valid",
                return_value=True,
            ), patch(
                "source.services.mercadopago_client.process_mercadopago_event_payload",
                side_effect=WebhookNoOpError("payment not found"),
            ):
                with self.assertRaises(WebhookNoOpError):
                    resolver_evento_webhook_mercadopago(
                        payload=payload,
                        x_signature="ok",
                        x_request_id="req-1",
                        db=session,
                    )
            session.commit()

            event = session.query(WebhookEvent).filter(WebhookEvent.event_key == "mp:event:evt-1").first()
            self.assertIsNotNone(event)
            assert event is not None
            self.assertEqual(event.status, "failed")
            self.assertEqual(int(event.attempt_count or 0), 1)
            self.assertIsNotNone(event.next_retry_at)
        finally:
            session.close()

    def test_non_retryable_noop_marks_event_processed(self) -> None:
        session = self.TestSession()
        try:
            payload = {"type": "payment", "data": {"id": "456"}, "id": "evt-2"}
            with patch(
                "source.services.mercadopago_client.is_mercadopago_signature_valid",
                return_value=True,
            ), patch(
                "source.services.mercadopago_client.process_mercadopago_event_payload",
                side_effect=WebhookNoOpError("unsupported topic"),
            ):
                with self.assertRaises(WebhookNoOpError):
                    resolver_evento_webhook_mercadopago(
                        payload=payload,
                        x_signature="ok",
                        x_request_id="req-2",
                        db=session,
                    )
            session.commit()

            event = session.query(WebhookEvent).filter(WebhookEvent.event_key == "mp:event:evt-2").first()
            self.assertIsNotNone(event)
            assert event is not None
            self.assertEqual(event.status, "processed")
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()

