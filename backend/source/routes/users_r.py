from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth.security import hash_password
from source.db.models import User
from source.db.session import get_db
from source.errors import raise_http_error_from_exception
from source.schemas import CreateUserRequest

router = APIRouter()


@router.post("/users")
def create_user(
    payload: CreateUserRequest,
    db: Session = Depends(get_db),
):
    user_data = payload.model_dump()
    normalized_email = user_data["email"].strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="email is required")

    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="email already exists")

    try:
        user = User(
            first_name=user_data["first_name"].strip(),
            last_name=user_data["last_name"].strip(),
            email=normalized_email,
            phone=None,
            password_hash=hash_password(user_data["password"]),
            is_admin=False,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as exc:
        raise_http_error_from_exception(exc, db=db)

    return {
        "data": {
            "id": int(user.id),
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "is_admin": bool(user.is_admin),
            "is_active": bool(user.is_active),
            "status": "created",
        }
    }
