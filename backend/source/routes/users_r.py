from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from source.dependencies.auth_d import require_admin
from source.db.session import get_db_transactional
from source.errors import raise_http_error_from_exception
from source.schemas import CreateUserRequest, ResolveUserRequest
from source.services.users_s import create_user as create_user_service
from source.services.users_s import resolve_user as resolve_user_service
from source.services.users_s import search_users as search_users_service

router = APIRouter()


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db_transactional),
):
    try:
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
