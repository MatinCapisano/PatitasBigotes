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

from source.db.models import Base, WebhookEvent
from source.exceptions import WebhookReplayConflictError
from source.services.mercadopago_client import WebhookNoOpError
from source.services.payment_s import replay_webhook_event_by_key


class AdminWebhookReplayTests(unittest.TestCase):
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

    def _seed_event(self, *, event_key: str, status: str) -> None:
        db = self.TestSession()
        try:
            db.add(
                WebhookEvent(
                    provider="mercadopago",
                    event_key=event_key,
                    status=status,
                    payload='{"type":"payment","data":{"id":"123"}}',
                    received_at=datetime.now(UTC),
                    processed_at=None,
                    last_error="boom" if status == "dead_letter" else None,
                    attempt_count=3 if status == "dead_letter" else 1,
                    next_retry_at=None,
                    dead_letter_at=datetime.now(UTC) if status == "dead_letter" else None,
                )
            )
            db.commit()
        finally:
            db.close()

    def test_replay_dead_letter_success_marks_processed(self) -> None:
        self._seed_event(event_key="mp:event:1", status="dead_letter")
        db = self.TestSession()
        try:
            with patch(
                "source.services.mercadopago_client.process_mercadopago_event_payload",
                return_value={"id": 99, "status": "paid"},
            ):
                result = replay_webhook_event_by_key(
                    provider="mercadopago",
                    event_key="mp:event:1",
                    db=db,
                )
            db.commit()

            row = db.query(WebhookEvent).filter(WebhookEvent.event_key == "mp:event:1").first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.status, "processed")
            self.assertTrue(result["processed"])
            self.assertEqual(result["new_status"], "processed")
        finally:
            db.close()

    def test_replay_dead_letter_payment_not_found_stays_retryable(self) -> None:
        self._seed_event(event_key="mp:event:2", status="dead_letter")
        db = self.TestSession()
        try:
            with patch(
                "source.services.mercadopago_client.process_mercadopago_event_payload",
                side_effect=WebhookNoOpError("payment not found"),
            ):
                result = replay_webhook_event_by_key(
                    provider="mercadopago",
                    event_key="mp:event:2",
                    db=db,
                )
            db.commit()

            row = db.query(WebhookEvent).filter(WebhookEvent.event_key == "mp:event:2").first()
            self.assertIsNotNone(row)
            assert row is not None
            self.assertEqual(row.status, "dead_letter")
            self.assertFalse(result["processed"])
            self.assertEqual(result["reason"], "payment not found")
        finally:
            db.close()

    def test_replay_processed_status_conflict(self) -> None:
        self._seed_event(event_key="mp:event:3", status="processed")
        db = self.TestSession()
        try:
            with self.assertRaises(WebhookReplayConflictError):
                replay_webhook_event_by_key(
                    provider="mercadopago",
                    event_key="mp:event:3",
                    db=db,
                )
        finally:
            db.close()

    def test_replay_unknown_event_returns_not_found(self) -> None:
        db = self.TestSession()
        try:
            with self.assertRaises(LookupError):
                replay_webhook_event_by_key(
                    provider="mercadopago",
                    event_key="mp:event:404",
                    db=db,
                )
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

