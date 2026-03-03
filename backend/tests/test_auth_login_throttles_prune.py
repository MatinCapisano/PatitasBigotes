import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.db.models import AuthLoginThrottle, Base
from source.services.auth_rate_limit_s import prune_auth_login_throttles


class AuthLoginThrottlesPruneTests(unittest.TestCase):
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

    def test_prune_deletes_only_old_rows_with_limit(self) -> None:
        db = self.TestSession()
        try:
            now = datetime.now(UTC)
            old_ts = now - timedelta(days=30)
            recent_ts = now - timedelta(days=1)

            db.add_all(
                [
                    AuthLoginThrottle(
                        scope="email",
                        key="old1@example.com",
                        failed_count=1,
                        window_started_at=old_ts,
                        blocked_until=None,
                        updated_at=old_ts,
                    ),
                    AuthLoginThrottle(
                        scope="ip",
                        key="1.1.1.1",
                        failed_count=2,
                        window_started_at=old_ts,
                        blocked_until=None,
                        updated_at=old_ts,
                    ),
                    AuthLoginThrottle(
                        scope="email",
                        key="recent@example.com",
                        failed_count=1,
                        window_started_at=recent_ts,
                        blocked_until=None,
                        updated_at=recent_ts,
                    ),
                ]
            )
            db.commit()

            deleted_first = prune_auth_login_throttles(
                now=now,
                older_than_days=14,
                limit=1,
                db=db,
            )
            db.commit()
            self.assertEqual(deleted_first, 1)

            deleted_second = prune_auth_login_throttles(
                now=now,
                older_than_days=14,
                limit=10,
                db=db,
            )
            db.commit()
            self.assertEqual(deleted_second, 1)

            remaining = db.query(AuthLoginThrottle).all()
            self.assertEqual(len(remaining), 1)
            self.assertEqual(remaining[0].key, "recent@example.com")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

