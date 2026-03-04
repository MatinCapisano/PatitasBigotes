import os
import sys
import unittest
from datetime import datetime, timedelta, UTC
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException
from fastapi import Response
from starlette.requests import Request

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DB_PATH = BACKEND_DIR / "tmp" / "test_auth_password_flows.db"
os.environ.setdefault("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
os.environ.setdefault("JWT_SECRET", "test-secret-auth-password-flows")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_ISSUER", "patitasbigotes-api")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "120")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "30")
os.environ.setdefault("APP_BASE_URL", "http://localhost:5173")

from auth.auth_s import issue_token_pair
from auth.security import verify_password
from source.db.models import AuthActionToken, Base, User, UserRefreshSession
from source.db.session import SessionLocal, engine
from source.routes.auth_r import (
    email_verify_confirm,
    email_verify_request,
    login,
    password_change,
    password_reset_confirm,
    password_reset_request,
    refresh,
    register,
    logout,
)
from source.schemas.auth_s import (
    EmailRequest,
    LoginRequest,
    PasswordChangeRequest,
    PasswordResetConfirmRequest,
    RegisterRequest,
    TokenRequest,
)
from source.services.auth_tokens_s import ACTION_EMAIL_VERIFY, ACTION_PASSWORD_RESET


class AuthPasswordFlowsTests(unittest.TestCase):
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

    def _request(self, *, ip: str = "127.0.0.1") -> Request:
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/auth/test",
            "headers": [],
            "client": (ip, 12345),
        }
        return Request(scope)

    def _request_with_cookies(self, *, cookies: dict[str, str], path: str = "/auth/test") -> Request:
        cookie_header = "; ".join(f"{key}={value}" for key, value in cookies.items())
        scope = {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": [(b"cookie", cookie_header.encode("utf-8"))],
            "client": ("127.0.0.1", 12345),
        }
        return Request(scope)

    @staticmethod
    def _cookie_value_from_response(response: Response, cookie_name: str) -> str:
        prefix = f"{cookie_name}="
        for key, value in response.raw_headers:
            if key.decode("latin-1").lower() != "set-cookie":
                continue
            cookie = value.decode("latin-1")
            if cookie.startswith(prefix):
                return cookie.split(";", 1)[0].split("=", 1)[1]
        return ""

    def _create_verified_user(self, *, email: str, password_hash: str) -> int:
        db = SessionLocal()
        try:
            user = User(
                first_name="Jane",
                last_name="Doe",
                email=email,
                password_hash=password_hash,
                has_account=True,
                is_admin=False,
                email_verified_at=datetime.now(UTC),
            )
            db.add(user)
            db.commit()
            return int(user.id)
        finally:
            db.close()

    def test_register_creates_unverified_user_and_sends_verification(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                response = register(
                    payload=RegisterRequest(
                        first_name="Ana",
                        last_name="Lopez",
                        email="ana@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            db.commit()
            self.assertTrue(response["data"]["registered"])
            user = db.query(User).filter(User.email == "ana@example.com").first()
            self.assertIsNotNone(user)
            assert user is not None
            self.assertIsNone(user.email_verified_at)
            token_row = (
                db.query(AuthActionToken)
                .filter(AuthActionToken.user_id == int(user.id), AuthActionToken.action == ACTION_EMAIL_VERIFY)
                .first()
            )
            self.assertIsNotNone(token_row)
            mocked_send.assert_called_once()
        finally:
            db.close()

    def test_login_rejects_unverified_user_403(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification"):
                register(
                    payload=RegisterRequest(
                        first_name="No",
                        last_name="Verify",
                        email="nover@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            db.commit()
            with self.assertRaises(HTTPException) as ctx:
                login(
                    payload=LoginRequest(email="nover@example.com", password="Strong!123"),
                    request=self._request(),
                    response=Response(),
                    db=db,
                )
            self.assertEqual(ctx.exception.status_code, 403)
            self.assertEqual(ctx.exception.detail, "email not verified")
        finally:
            db.close()

    def test_login_sets_auth_cookies_and_hides_tokens_in_body(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Cookie",
                        last_name="Login",
                        email="cookie-login@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            token = mocked_send.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)

            response = Response()
            payload = login(
                payload=LoginRequest(email="cookie-login@example.com", password="Strong!123"),
                request=self._request(),
                response=response,
                db=db,
            )
            self.assertTrue(payload["data"]["logged_in"])
            self.assertIn("access_expires_in_minutes", payload["data"])
            self.assertNotIn("access_token", payload["data"])
            self.assertNotIn("refresh_token", payload["data"])

            access_cookie = self._cookie_value_from_response(response, "pb_at")
            refresh_cookie = self._cookie_value_from_response(response, "pb_rt")
            self.assertTrue(access_cookie)
            self.assertTrue(refresh_cookie)
        finally:
            db.close()

    def test_refresh_and_logout_work_with_refresh_cookie(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Cookie",
                        last_name="Refresh",
                        email="cookie-refresh@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            token = mocked_send.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)

            login_response = Response()
            login(
                payload=LoginRequest(email="cookie-refresh@example.com", password="Strong!123"),
                request=self._request(),
                response=login_response,
                db=db,
            )
            db.commit()
            refresh_cookie_value = self._cookie_value_from_response(login_response, "pb_rt")
            self.assertTrue(refresh_cookie_value)

            refresh_response = Response()
            refreshed = refresh(
                request=self._request_with_cookies(
                    cookies={"pb_rt": refresh_cookie_value},
                    path="/auth/refresh",
                ),
                response=refresh_response,
                db=db,
            )
            db.commit()
            self.assertTrue(refreshed["data"]["refreshed"])
            next_refresh_cookie = self._cookie_value_from_response(refresh_response, "pb_rt")
            self.assertTrue(next_refresh_cookie)

            logout_response = Response()
            logged_out = logout(
                request=self._request_with_cookies(
                    cookies={"pb_rt": next_refresh_cookie},
                    path="/auth/logout",
                ),
                response=logout_response,
                db=db,
            )
            self.assertTrue(logged_out["data"]["logged_out"])
            clear_access_cookie = self._cookie_value_from_response(logout_response, "pb_at")
            clear_refresh_cookie = self._cookie_value_from_response(logout_response, "pb_rt")
            self.assertIn(clear_access_cookie, {"", "\"\""})
            self.assertIn(clear_refresh_cookie, {"", "\"\""})
        finally:
            db.close()

    def test_verify_confirm_marks_user_verified_and_token_single_use(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Vic",
                        last_name="Tor",
                        email="victor@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            args, kwargs = mocked_send.call_args
            verify_link = kwargs["verify_link"] if "verify_link" in kwargs else args[1]
            token = verify_link.split("token=")[1]

            response = email_verify_confirm(payload=TokenRequest(token=token), db=db)
            db.commit()
            self.assertTrue(response["data"]["verified"])

            user = db.query(User).filter(User.email == "victor@example.com").first()
            self.assertIsNotNone(user)
            assert user is not None
            self.assertIsNotNone(user.email_verified_at)

            with self.assertRaises(HTTPException) as second_ctx:
                email_verify_confirm(payload=TokenRequest(token=token), db=db)
            self.assertEqual(second_ctx.exception.status_code, 400)
        finally:
            db.close()

    def test_verify_token_expired_rejected(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Ex",
                        last_name="Pired",
                        email="expired@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            args, kwargs = mocked_send.call_args
            token = (kwargs.get("verify_link") or args[1]).split("token=")[1]
            row = db.query(AuthActionToken).filter(AuthActionToken.action == ACTION_EMAIL_VERIFY).first()
            self.assertIsNotNone(row)
            assert row is not None
            row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            db.flush()

            with self.assertRaises(HTTPException) as ctx:
                email_verify_confirm(payload=TokenRequest(token=token), db=db)
            self.assertEqual(ctx.exception.status_code, 400)
        finally:
            db.close()

    def test_verify_resend_invalidates_previous_token(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Re",
                        last_name="Send",
                        email="resend@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(ip="10.0.0.1"),
                    db=db,
                )
                first_token = (mocked_send.call_args.kwargs["verify_link"]).split("token=")[1]

                row = db.query(AuthActionToken).filter(AuthActionToken.action == ACTION_EMAIL_VERIFY).first()
                assert row is not None
                row.used_at = datetime.now(UTC) - timedelta(minutes=1)
                db.flush()

                email_verify_request(
                    payload=EmailRequest(email="resend@example.com"),
                    request=self._request(ip="10.0.0.1"),
                    db=db,
                )
                second_token = (mocked_send.call_args.kwargs["verify_link"]).split("token=")[1]

            self.assertNotEqual(first_token, second_token)
        finally:
            db.close()

    def test_password_reset_request_is_non_enumerable(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_password_reset") as mocked_send:
                existing = password_reset_request(
                    payload=EmailRequest(email="ghost@example.com"),
                    request=self._request(ip="20.0.0.1"),
                    db=db,
                )
                missing = password_reset_request(
                    payload=EmailRequest(email="missing@example.com"),
                    request=self._request(ip="20.0.0.2"),
                    db=db,
                )
            self.assertEqual(existing, missing)
            mocked_send.assert_not_called()
        finally:
            db.close()

    def test_password_reset_confirm_updates_hash_and_bumps_token_version(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_verify:
                register(
                    payload=RegisterRequest(
                        first_name="Res",
                        last_name="Et",
                        email="reset@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(ip="30.0.0.1"),
                    db=db,
                )
            token = mocked_verify.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)

            user = db.query(User).filter(User.email == "reset@example.com").first()
            assert user is not None
            before_tv = int(user.token_version)

            with patch("source.routes.auth_r.send_password_reset") as mocked_reset:
                password_reset_request(
                    payload=EmailRequest(email="reset@example.com"),
                    request=self._request(ip="30.0.0.1"),
                    db=db,
                )
            reset_token = mocked_reset.call_args.kwargs["reset_link"].split("token=")[1]

            password_reset_confirm(
                payload=PasswordResetConfirmRequest(token=reset_token, new_password="NewStrong!123"),
                db=db,
            )
            db.commit()

            db.refresh(user)
            self.assertEqual(int(user.token_version), before_tv + 1)
            self.assertTrue(verify_password("NewStrong!123", user.password_hash))
        finally:
            db.close()

    def test_password_change_requires_current_password(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Cha",
                        last_name="Nge",
                        email="change@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            token = mocked_send.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)
            user = db.query(User).filter(User.email == "change@example.com").first()
            assert user is not None

            with self.assertRaises(HTTPException) as ctx:
                password_change(
                    payload=PasswordChangeRequest(
                        current_password="wrong!123",
                        new_password="Another!123",
                    ),
                    current_user={"sub": str(user.id), "is_admin": False, "tv": int(user.token_version)},
                    db=db,
                )
            self.assertEqual(ctx.exception.status_code, 400)
        finally:
            db.close()

    def test_password_change_rejects_wrong_current_password(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Cha",
                        last_name="Nge2",
                        email="change2@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            token = mocked_send.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)
            user = db.query(User).filter(User.email == "change2@example.com").first()
            assert user is not None

            with self.assertRaises(HTTPException) as ctx:
                password_change(
                    payload=PasswordChangeRequest(
                        current_password="invalid!123",
                        new_password="Another!123",
                    ),
                    current_user={"sub": str(user.id), "is_admin": False, "tv": int(user.token_version)},
                    db=db,
                )
            self.assertEqual(ctx.exception.status_code, 400)
            self.assertEqual(ctx.exception.detail, "current password is invalid")
        finally:
            db.close()

    def test_password_change_invalidates_refresh_session(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification") as mocked_send:
                register(
                    payload=RegisterRequest(
                        first_name="Ref",
                        last_name="Resh",
                        email="refresh@example.com",
                        password="Strong!123",
                    ),
                    request=self._request(),
                    db=db,
                )
            token = mocked_send.call_args.kwargs["verify_link"].split("token=")[1]
            email_verify_confirm(payload=TokenRequest(token=token), db=db)

            user = db.query(User).filter(User.email == "refresh@example.com").first()
            assert user is not None
            issue_token_pair(user=user, db=db)
            db.flush()
            session_row = (
                db.query(UserRefreshSession)
                .filter(UserRefreshSession.user_id == int(user.id))
                .first()
            )
            self.assertIsNotNone(session_row)

            password_change(
                payload=PasswordChangeRequest(
                    current_password="Strong!123",
                    new_password="Changed!123",
                ),
                current_user={"sub": str(user.id), "is_admin": False, "tv": int(user.token_version)},
                db=db,
            )
            db.commit()

            session_after = (
                db.query(UserRefreshSession)
                .filter(UserRefreshSession.user_id == int(user.id))
                .first()
            )
            self.assertIsNone(session_after)
        finally:
            db.close()

    def test_reset_request_rate_limited_by_ip_and_email(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_password_reset"):
                password_reset_request(
                    payload=EmailRequest(email="rate-reset@example.com"),
                    request=self._request(ip="50.0.0.1"),
                    db=db,
                )
                with self.assertRaises(HTTPException) as ctx:
                    password_reset_request(
                        payload=EmailRequest(email="rate-reset@example.com"),
                        request=self._request(ip="50.0.0.1"),
                        db=db,
                    )
            self.assertEqual(ctx.exception.status_code, 429)
        finally:
            db.close()

    def test_verify_resend_rate_limited_by_ip_and_email(self) -> None:
        db = SessionLocal()
        try:
            with patch("source.routes.auth_r.send_email_verification"):
                email_verify_request(
                    payload=EmailRequest(email="rate-verify@example.com"),
                    request=self._request(ip="60.0.0.1"),
                    db=db,
                )
                with self.assertRaises(HTTPException) as ctx:
                    email_verify_request(
                        payload=EmailRequest(email="rate-verify@example.com"),
                        request=self._request(ip="60.0.0.1"),
                        db=db,
                    )
            self.assertEqual(ctx.exception.status_code, 429)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()

