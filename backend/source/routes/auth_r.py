from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from auth.auth_s import (
    authenticate_user,
    issue_token_pair,
    logout_with_refresh_token,
    refresh_with_token,
)
from source.dependencies.auth_d import bearer_scheme
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.schemas import LoginRequest
from source.services.auth_rate_limit_s import (
    LoginRateLimitExceededError,
    clear_login_failures,
    enforce_login_rate_limit,
    register_login_failure,
)

router = APIRouter()


def _extract_client_ip(request: Request) -> str:
    forwarded = str(request.headers.get("x-forwarded-for", "")).strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client is not None and request.client.host:
        return str(request.client.host).strip()
    return "unknown"


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db_transactional),
):
    client_ip = _extract_client_ip(request)
    normalized_email = str(payload.email).strip().lower()
    try:
        enforce_login_rate_limit(email=normalized_email, ip=client_ip, db=db)
        user = authenticate_user(
            email=payload.email,
            password=payload.password,
            db=db,
        )
        clear_login_failures(email=normalized_email, ip=client_ip, db=db)
        tokens = issue_token_pair(user=user, db=db)
    except LoginRateLimitExceededError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="too many attempts, try later",
        )
    except (LookupError, ValueError):
        register_login_failure(email=normalized_email, ip=client_ip, db=db)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid credentials",
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": tokens}


@router.post("/auth/refresh")
def refresh(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_transactional),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        tokens = refresh_with_token(refresh_token=credentials.credentials, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": tokens}


@router.post("/auth/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db_transactional),
):
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    try:
        logout_with_refresh_token(refresh_token=credentials.credentials, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)
    return {"data": {"logged_out": True}}
