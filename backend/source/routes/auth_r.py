from fastapi import APIRouter, Depends, HTTPException, status
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

router = APIRouter()


@router.post("/auth/login")
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db_transactional),
):
    try:
        user = authenticate_user(
            email=payload.email,
            password=payload.password,
            db=db,
        )
        tokens = issue_token_pair(user=user, db=db)
    except (LookupError, ValueError):
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
