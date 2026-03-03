from __future__ import annotations

from datetime import datetime, timedelta, UTC
import hashlib
import json
import secrets

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from source.db.models import AuthActionToken, User

ACTION_EMAIL_VERIFY = "email_verify"
ACTION_PASSWORD_RESET = "password_reset"
ALLOWED_ACTIONS = {ACTION_EMAIL_VERIFY, ACTION_PASSWORD_RESET}


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_action(action: str) -> str:
    normalized = str(action or "").strip().lower()
    if normalized not in ALLOWED_ACTIONS:
        raise ValueError("invalid auth token action")
    return normalized


def generate_raw_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(raw: str) -> str:
    normalized = str(raw or "").strip()
    if not normalized:
        raise ValueError("token is required")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def invalidate_active_tokens(
    *,
    user_id: int,
    action: str,
    db: Session,
) -> int:
    normalized_action = _normalize_action(action)
    now = _utc_now()
    rows = (
        db.query(AuthActionToken)
        .filter(
            AuthActionToken.user_id == int(user_id),
            AuthActionToken.action == normalized_action,
            AuthActionToken.used_at.is_(None),
            AuthActionToken.expires_at > now,
        )
        .all()
    )
    for row in rows:
        row.used_at = now
    if rows:
        db.flush()
    return len(rows)


def create_one_time_token(
    *,
    user_id: int,
    action: str,
    ttl: timedelta,
    requested_ip: str | None,
    db: Session,
    meta: dict | None = None,
) -> str:
    normalized_action = _normalize_action(action)
    ttl_seconds = int(ttl.total_seconds())
    if ttl_seconds <= 0:
        raise ValueError("ttl must be greater than 0")

    invalidate_active_tokens(user_id=int(user_id), action=normalized_action, db=db)

    raw_token = generate_raw_token()
    token_hash = hash_token(raw_token)
    now = _utc_now()
    token_row = AuthActionToken(
        user_id=int(user_id),
        action=normalized_action,
        token_hash=token_hash,
        expires_at=now + ttl,
        used_at=None,
        requested_ip=(str(requested_ip or "").strip() or None),
        meta=json.dumps(meta, separators=(",", ":"), ensure_ascii=True) if isinstance(meta, dict) else None,
        created_at=now,
    )
    db.add(token_row)
    db.flush()
    return raw_token


def consume_one_time_token(
    *,
    raw_token: str,
    action: str,
    db: Session,
) -> User:
    normalized_action = _normalize_action(action)
    normalized_hash = hash_token(raw_token)
    now = _utc_now()
    token_row = (
        db.query(AuthActionToken)
        .filter(
            AuthActionToken.token_hash == normalized_hash,
            AuthActionToken.action == normalized_action,
        )
        .with_for_update()
        .first()
    )
    if token_row is None:
        raise ValueError("invalid token")
    if token_row.used_at is not None:
        raise ValueError("token already used")
    expires_at = _as_utc(token_row.expires_at)
    if expires_at <= now:
        raise ValueError("token expired")

    user = (
        db.query(User)
        .filter(User.id == int(token_row.user_id))
        .with_for_update()
        .first()
    )
    if user is None:
        raise LookupError("user not found")

    token_row.used_at = now
    db.flush()
    return user


def prune_auth_action_tokens(
    *,
    now: datetime,
    older_than_days: int,
    db: Session,
    limit: int = 500,
) -> int:
    safe_limit = max(1, int(limit))
    threshold = now - timedelta(days=max(1, int(older_than_days)))
    expired_ids = [
        row.id
        for row in (
            db.query(AuthActionToken.id)
            .filter(
                or_(
                    AuthActionToken.expires_at <= now,
                    and_(
                        AuthActionToken.used_at.is_not(None),
                        AuthActionToken.used_at <= threshold,
                    ),
                )
            )
            .order_by(AuthActionToken.id.asc())
            .limit(safe_limit)
            .all()
        )
    ]
    if not expired_ids:
        return 0
    deleted = (
        db.query(AuthActionToken)
        .filter(AuthActionToken.id.in_(expired_ids))
        .delete(synchronize_session=False)
    )
    db.flush()
    return int(deleted or 0)

