import sys
import unittest
import json
import base64
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from auth import security


class SecurityTests(unittest.TestCase):
    @staticmethod
    def _decode_payload_without_verification(token: str) -> dict:
        payload_segment = token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        payload_bytes = base64.urlsafe_b64decode(payload_segment + padding)
        return json.loads(payload_bytes.decode("utf-8"))

    def test_verify_password_invalid_hash_returns_false(self) -> None:
        self.assertFalse(security.verify_password("plain", "not-a-valid-hash"))

    def test_create_access_token_zero_delta_uses_immediate_expiry(self) -> None:
        token = security.create_access_token(
            {"sub": "user-1"},
            expires_delta=timedelta(0),
        )
        claims = self._decode_payload_without_verification(token)
        exp_ts = claims["exp"]
        now_ts = datetime.now(timezone.utc).timestamp()

        self.assertLessEqual(abs(exp_ts - now_ts), 5)

    def test_decode_access_token_invalid_token_sets_cause(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            security.decode_access_token("invalid-token")

        self.assertEqual(str(ctx.exception), "Invalid token")
        self.assertIsNotNone(ctx.exception.__cause__)


if __name__ == "__main__":
    unittest.main()
