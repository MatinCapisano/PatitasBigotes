from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from source.db.models import Turn, User

BUSINESS_TIMEZONE = ZoneInfo("America/Argentina/Buenos_Aires")
BUSINESS_OPEN_HOUR = 13
BUSINESS_CLOSE_HOUR = 20


def _turn_to_dict(turn: Turn) -> dict:
    return {
        "id": turn.id,
        "user_id": turn.user_id,
        "status": turn.status,
        "scheduled_at": turn.scheduled_at,
        "notes": turn.notes,
        "created_at": turn.created_at,
        "updated_at": turn.updated_at,
    }


def _turn_to_admin_dict(turn: Turn) -> dict:
    user = turn.user
    return {
        "id": int(turn.id),
        "status": turn.status,
        "scheduled_at": turn.scheduled_at,
        "notes": turn.notes,
        "created_at": turn.created_at,
        "updated_at": turn.updated_at,
        "customer": {
            "id": int(user.id) if user is not None else None,
            "first_name": user.first_name if user is not None else None,
            "last_name": user.last_name if user is not None else None,
            "phone": user.phone if user is not None else None,
        },
    }


def _normalize_scheduled_at(scheduled_at: datetime | None) -> datetime | None:
    if scheduled_at is None:
        return None
    if scheduled_at.tzinfo is None:
        return scheduled_at.replace(tzinfo=BUSINESS_TIMEZONE)
    return scheduled_at.astimezone(BUSINESS_TIMEZONE)


def _validate_business_slot(scheduled_at: datetime | None) -> None:
    if scheduled_at is None:
        return
    local_dt = _normalize_scheduled_at(scheduled_at)
    assert local_dt is not None
    if int(local_dt.weekday()) > 4:
        raise ValueError("turns are only available from monday to friday")
    minute_of_day = int(local_dt.hour) * 60 + int(local_dt.minute)
    starts_minute = BUSINESS_OPEN_HOUR * 60
    closes_minute = BUSINESS_CLOSE_HOUR * 60
    if minute_of_day < starts_minute or minute_of_day > closes_minute:
        raise ValueError("turn hour must be between 13:00 and 20:00")


def create_turn_for_user(
    *,
    user_id: int,
    scheduled_at: datetime | None = None,
    notes: str | None = None,
    db: Session,
) -> dict:
    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )
    if user is None:
        raise LookupError("user not found")

    normalized_notes = None if notes is None else str(notes).strip() or None
    normalized_scheduled_at = _normalize_scheduled_at(scheduled_at)
    _validate_business_slot(normalized_scheduled_at)
    turn = Turn(
        user_id=user_id,
        status="pending",
        scheduled_at=normalized_scheduled_at,
        notes=normalized_notes,
    )
    db.add(turn)
    db.flush()
    db.refresh(turn)
    return _turn_to_dict(turn)


def list_turns_for_admin(
    *,
    db: Session,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    safe_limit = max(1, min(int(limit), 200))
    query = db.query(Turn).join(User, Turn.user_id == User.id)
    if status is not None:
        normalized = str(status).strip().lower()
        if normalized not in {"pending", "confirmed", "cancelled"}:
            raise ValueError("invalid status filter")
        query = query.filter(Turn.status == normalized)
    rows = query.order_by(Turn.created_at.desc(), Turn.id.desc()).limit(safe_limit).all()
    return [_turn_to_admin_dict(row) for row in rows]


def update_turn_status_for_admin(
    *,
    turn_id: int,
    new_status: str,
    db: Session,
) -> dict:
    normalized_status = str(new_status).strip().lower()
    if normalized_status not in {"confirmed", "cancelled"}:
        raise ValueError("invalid status")

    turn = (
        db.query(Turn)
        .join(User, Turn.user_id == User.id)
        .filter(Turn.id == int(turn_id))
        .first()
    )
    if turn is None:
        raise LookupError("turn not found")

    current_status = str(turn.status or "").strip().lower()
    if current_status not in {"pending", normalized_status}:
        raise ValueError("turn status cannot be changed from current state")
    turn.status = normalized_status
    turn.updated_at = datetime.now(UTC)
    db.flush()
    db.refresh(turn)
    return _turn_to_admin_dict(turn)
