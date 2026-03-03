from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from source.dependencies.auth_d import require_admin
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.schemas import CreateUserRequest, ResolveUserRequest
from source.services.anti_abuse_s import enforce_public_signup_limits
from source.services.users_s import create_user as create_user_service
from source.services.users_s import resolve_user as resolve_user_service
from source.services.users_s import search_users as search_users_service

router = APIRouter()


def _client_ip_from_request(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    request: Request,
    db: Session = Depends(get_db_transactional),
):
    try:
        enforce_public_signup_limits(
            client_ip=_client_ip_from_request(request),
            email=payload.email,
            db=db,
        )
        created_user = create_user_service(payload=payload, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": created_user}


@router.get("/users/search")
def search_users(
    email: str | None = None,
    dni: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    phone: str | None = None,
    limit: int = 20,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        users = search_users_service(
            db=db,
            email=email,
            dni=dni,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            limit=limit,
        )
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": users}


@router.post("/users/resolve")
def resolve_user(
    payload: ResolveUserRequest,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db_transactional),
):
    try:
        result = resolve_user_service(payload=payload, db=db)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {"data": result}
