import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import AuthLoginThrottle, Base
from source.services.auth_rate_limit_s import (
    LoginRateLimitExceededError,
    clear_login_failures,
    enforce_login_rate_limit,
    register_login_failure,
)


class AuthLoginRateLimitTests(unittest.TestCase):
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

    def test_six_failures_then_next_enforce_blocks(self) -> None:
        db = self.TestSession()
        try:
            email = "rate@example.com"
            ip = "10.0.0.1"
            for _ in range(6):
                enforce_login_rate_limit(email=email, ip=ip, db=db)
                register_login_failure(email=email, ip=ip, db=db)
            with self.assertRaises(LoginRateLimitExceededError):
                enforce_login_rate_limit(email=email, ip=ip, db=db)
        finally:
            db.close()

    def test_lockout_expires_after_block_window(self) -> None:
        db = self.TestSession()
        try:
            email = "lock@example.com"
            ip = "10.0.0.2"
            for _ in range(6):
                register_login_failure(email=email, ip=ip, db=db)
            with self.assertRaises(LoginRateLimitExceededError):
                enforce_login_rate_limit(email=email, ip=ip, db=db)

            now = datetime.now(timezone.utc)
            rows = db.query(AuthLoginThrottle).all()
            for row in rows:
                row.blocked_until = now - timedelta(seconds=1)
            db.flush()

            enforce_login_rate_limit(email=email, ip=ip, db=db)
        finally:
            db.close()

    def test_email_scope_blocks_even_with_different_ip(self) -> None:
        db = self.TestSession()
        try:
            email = "email-scope@example.com"
            for i in range(6):
                register_login_failure(email=email, ip=f"10.0.0.{i + 1}", db=db)
            with self.assertRaises(LoginRateLimitExceededError):
                enforce_login_rate_limit(email=email, ip="10.0.1.99", db=db)
        finally:
            db.close()

    def test_ip_scope_blocks_even_with_different_email(self) -> None:
        db = self.TestSession()
        try:
            ip = "192.168.1.88"
            for i in range(6):
                register_login_failure(email=f"user{i}@example.com", ip=ip, db=db)
            with self.assertRaises(LoginRateLimitExceededError):
                enforce_login_rate_limit(email="newuser@example.com", ip=ip, db=db)
        finally:
            db.close()

    def test_success_clear_resets_counters_and_block(self) -> None:
        db = self.TestSession()
        try:
            email = "clear@example.com"
            ip = "10.0.0.7"
            for _ in range(3):
                register_login_failure(email=email, ip=ip, db=db)

            clear_login_failures(email=email, ip=ip, db=db)

            rows = (
                db.query(AuthLoginThrottle)
                .filter(AuthLoginThrottle.key.in_([email, ip]))
                .all()
            )
            self.assertEqual(len(rows), 2)
            for row in rows:
                self.assertEqual(int(row.failed_count), 0)
                self.assertIsNone(row.blocked_until)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
