import sys
import unittest
from pathlib import Path

from fastapi import HTTPException

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.services import anti_abuse_s
from source.services.anti_abuse_s import enforce_public_signup_limits


class SignupRateLimitTests(unittest.TestCase):
    def setUp(self) -> None:
        anti_abuse_s._ip_hits.clear()
        anti_abuse_s._email_hits.clear()
        anti_abuse_s._last_email_hit.clear()

    def test_second_signup_attempt_too_soon_is_blocked(self) -> None:
        enforce_public_signup_limits(
            client_ip="10.0.0.1",
            email="signup@example.com",
        )

        with self.assertRaises(HTTPException) as ctx:
            enforce_public_signup_limits(
                client_ip="10.0.0.1",
                email="signup@example.com",
            )
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.detail, "please wait before retrying signup")

    def test_signup_limit_blocks_by_ip(self) -> None:
        for i in range(anti_abuse_s.IP_MAX_REQUESTS):
            enforce_public_signup_limits(
                client_ip="10.0.0.2",
                email=f"user{i}@example.com",
            )

        with self.assertRaises(HTTPException) as ctx:
            enforce_public_signup_limits(
                client_ip="10.0.0.2",
                email="overflow@example.com",
            )
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertEqual(ctx.exception.detail, "too many signup attempts from this ip")


if __name__ == "__main__":
    unittest.main()
