from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException, status

IP_WINDOW = timedelta(minutes=5)
IP_MAX_REQUESTS = 20
EMAIL_WINDOW = timedelta(minutes=10)
EMAIL_MAX_REQUESTS = 6
EMAIL_MIN_INTERVAL_SECONDS = 20

_lock = Lock()
_ip_hits: dict[str, deque[datetime]] = defaultdict(deque)
_email_hits: dict[str, deque[datetime]] = defaultdict(deque)
_last_email_hit: dict[str, datetime] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _prune(queue: deque[datetime], *, now: datetime, window: timedelta) -> None:
    cutoff = now - window
    while queue and queue[0] < cutoff:
        queue.popleft()


def _normalize_email(value: str) -> str:
    return str(value).strip().lower()


def enforce_public_guest_checkout_limits(
    *,
    client_ip: str,
    email: str,
    website: str | None = None,
) -> None:
    if website is not None and str(website).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid request",
        )

    normalized_ip = str(client_ip).strip() or "unknown"
    normalized_email = _normalize_email(email)
    now = _utc_now()

    with _lock:
        ip_queue = _ip_hits[normalized_ip]
        _prune(ip_queue, now=now, window=IP_WINDOW)
        if len(ip_queue) >= IP_MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many checkout attempts from this ip",
            )

        email_queue = _email_hits[normalized_email]
        _prune(email_queue, now=now, window=EMAIL_WINDOW)
        if len(email_queue) >= EMAIL_MAX_REQUESTS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="too many checkout attempts for this email",
            )

        last_hit = _last_email_hit.get(normalized_email)
        if last_hit is not None:
            elapsed = (now - last_hit).total_seconds()
            if elapsed < EMAIL_MIN_INTERVAL_SECONDS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="please wait before retrying checkout",
                )

        ip_queue.append(now)
        email_queue.append(now)
        _last_email_hit[normalized_email] = now
