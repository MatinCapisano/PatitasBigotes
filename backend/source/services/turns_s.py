from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from source.db.models import Turn, User


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
    turn = Turn(
        user_id=user_id,
        status="pending",
        scheduled_at=scheduled_at,
        notes=normalized_notes,
    )
    db.add(turn)
    db.flush()
    db.refresh(turn)
    return _turn_to_dict(turn)
