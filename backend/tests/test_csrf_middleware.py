import asyncio
import os
import sys
import unittest
from pathlib import Path

from starlette.requests import Request
from starlette.responses import Response

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from source.dependencies.csrf_d import CSRFMiddleware


class CSRFMiddlewareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._env_backup = dict(os.environ)
        os.environ["CORS_ALLOW_ORIGINS"] = "http://localhost:5173,http://127.0.0.1:5173"

    @classmethod
    def tearDownClass(cls) -> None:
        os.environ.clear()
        os.environ.update(cls._env_backup)

    @staticmethod
    def _request(*, method: str, path: str, headers: dict[str, str] | None = None) -> Request:
        headers = headers or {}
        raw_headers = [(k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()]
        scope = {
            "type": "http",
            "method": method.upper(),
            "path": path,
            "headers": raw_headers,
            "client": ("127.0.0.1", 12345),
            "query_string": b"",
            "scheme": "http",
            "server": ("testserver", 80),
        }
        return Request(scope)

    @staticmethod
    async def _call_next(_: Request) -> Response:
        return Response(status_code=200)

    def _dispatch(self, request: Request) -> Response:
        middleware = CSRFMiddleware(app=lambda scope, receive, send: None)
        return asyncio.run(middleware.dispatch(request, self._call_next))

    def test_post_with_allowed_origin_is_accepted(self) -> None:
        response = self._dispatch(
            self._request(
                method="POST",
                path="/protected",
                headers={"Origin": "http://localhost:5173"},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_post_with_disallowed_origin_is_rejected(self) -> None:
        response = self._dispatch(
            self._request(
                method="POST",
                path="/protected",
                headers={"Origin": "https://evil.example"},
            )
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"csrf origin check failed", response.body)

    def test_post_with_allowed_referer_is_accepted(self) -> None:
        response = self._dispatch(
            self._request(
                method="POST",
                path="/protected",
                headers={"Referer": "http://localhost:5173/some/path"},
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_post_without_origin_or_referer_is_rejected(self) -> None:
        response = self._dispatch(self._request(method="POST", path="/protected"))
        self.assertEqual(response.status_code, 403)

    def test_webhook_path_is_exempt(self) -> None:
        response = self._dispatch(self._request(method="POST", path="/payments/webhook/mercadopago"))
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
