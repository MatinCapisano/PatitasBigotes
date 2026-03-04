from __future__ import annotations

from fastapi import Request, Response

from source.db.config import (
    get_auth_cookie_access_name,
    get_auth_cookie_domain,
    get_auth_cookie_path_access,
    get_auth_cookie_path_refresh,
    get_auth_cookie_refresh_name,
    get_auth_cookie_samesite,
    get_auth_cookie_secure,
)


def _cookie_common_kwargs() -> dict:
    kwargs: dict[str, object] = {
        "httponly": True,
        "secure": get_auth_cookie_secure(),
        "samesite": get_auth_cookie_samesite(),
    }
    domain = get_auth_cookie_domain()
    if domain:
        kwargs["domain"] = domain
    return kwargs


def set_auth_cookies(
    *,
    response: Response,
    access_token: str,
    refresh_token: str,
    access_max_age_seconds: int,
    refresh_max_age_seconds: int,
) -> None:
    common = _cookie_common_kwargs()
    response.set_cookie(
        key=get_auth_cookie_access_name(),
        value=access_token,
        max_age=int(access_max_age_seconds),
        path=get_auth_cookie_path_access(),
        **common,
    )
    response.set_cookie(
        key=get_auth_cookie_refresh_name(),
        value=refresh_token,
        max_age=int(refresh_max_age_seconds),
        path=get_auth_cookie_path_refresh(),
        **common,
    )


def clear_auth_cookies(*, response: Response) -> None:
    common = _cookie_common_kwargs()
    response.set_cookie(
        key=get_auth_cookie_access_name(),
        value="",
        max_age=0,
        expires=0,
        path=get_auth_cookie_path_access(),
        **common,
    )
    response.set_cookie(
        key=get_auth_cookie_refresh_name(),
        value="",
        max_age=0,
        expires=0,
        path=get_auth_cookie_path_refresh(),
        **common,
    )


def get_access_token_from_request(request: Request) -> str:
    return str(request.cookies.get(get_auth_cookie_access_name(), "")).strip()


def get_refresh_token_from_request(request: Request) -> str:
    return str(request.cookies.get(get_auth_cookie_refresh_name(), "")).strip()
