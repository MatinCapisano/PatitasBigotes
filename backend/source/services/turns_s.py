from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime

from sqlalchemy.orm import Session

from source.db.models import Turn, User
from source.db.session import SessionLocal


@contextmanager
def _session_scope(db: Session | None):
    owns_session = db is None
    session = db or SessionLocal()
    try:
        yield session, owns_session
    finally:
        if owns_session:
            session.close()


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
    db: Session | None = None,
) -> dict:
    with _session_scope(db) as (session, owns_session):
        user = (
            session.query(User)
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
        session.add(turn)
        session.flush()
        if owns_session:
            session.commit()
        session.refresh(turn)
        return _turn_to_dict(turn)
