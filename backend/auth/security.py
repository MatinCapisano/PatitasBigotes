from datetime import datetime, timedelta
from typing import Optional

from jose import ExpiredSignatureError, JWTError, jwt
from passlib.exc import InvalidHashError, UnknownHashError
from passlib.context import CryptContext


# En producción esto debe venir de variables de entorno
SECRET_KEY = "CAMBIAR_ESTO_EN_PRODUCCION"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)


def hash_password(password: str) -> str:
    """
    Recibe una contraseña en texto plano
    y devuelve el hash seguro.
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica una contraseña contra su hash.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (UnknownHashError, InvalidHashError, ValueError, TypeError):
        return False



def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Genera un JWT firmado con expiración.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return encoded_jwt



def decode_access_token(token: str) -> dict:
    """
    Decodifica un JWT y devuelve el payload.
    Lanza excepción si es inválido.
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        return payload
    except ExpiredSignatureError as exc:
        raise ValueError("Token expired") from exc
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
