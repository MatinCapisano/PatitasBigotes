from __future__ import annotations

import argparse
from datetime import UTC, datetime
import logging
import os
import time

from source.db.session import SessionLocal
from source.services.auth_tokens_s import prune_auth_action_tokens

DEFAULT_INTERVAL_MINUTES = 1440
DEFAULT_OLDER_THAN_DAYS = 7
DEFAULT_BATCH_SIZE = 500

logger = logging.getLogger("auth_action_tokens_prune_job")


def _interval_minutes() -> int:
    raw = str(os.getenv("AUTH_ACTION_TOKENS_PRUNE_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES)).strip()
    value = int(raw)
    if value <= 0:
        raise RuntimeError("AUTH_ACTION_TOKENS_PRUNE_INTERVAL_MINUTES must be greater than 0")
    return value


def _older_than_days() -> int:
    raw = str(os.getenv("AUTH_ACTION_TOKENS_PRUNE_OLDER_THAN_DAYS", DEFAULT_OLDER_THAN_DAYS)).strip()
    value = int(raw)
    if value <= 0:
        raise RuntimeError("AUTH_ACTION_TOKENS_PRUNE_OLDER_THAN_DAYS must be greater than 0")
    return value


def _batch_size() -> int:
    raw = str(os.getenv("AUTH_ACTION_TOKENS_PRUNE_BATCH_SIZE", DEFAULT_BATCH_SIZE)).strip()
    value = int(raw)
    if value <= 0:
        raise RuntimeError("AUTH_ACTION_TOKENS_PRUNE_BATCH_SIZE must be greater than 0")
    return value


def run_once(*, older_than_days: int, batch_size: int) -> int:
    db = SessionLocal()
    try:
        deleted = prune_auth_action_tokens(
            now=datetime.now(UTC),
            older_than_days=older_than_days,
            limit=batch_size,
            db=db,
        )
        db.commit()
        logger.info(
            "event=auth_action_tokens_prune_run deleted=%s older_than_days=%s",
            int(deleted),
            int(older_than_days),
        )
        return int(deleted)
    except Exception:
        db.rollback()
        logger.exception("event=auth_action_tokens_prune_failed")
        raise
    finally:
        db.close()


def run_forever(*, interval_minutes: int, older_than_days: int, batch_size: int) -> None:
    interval_seconds = int(interval_minutes) * 60
    logger.info(
        (
            "event=auth_action_tokens_prune_started interval_minutes=%s "
            "older_than_days=%s batch_size=%s"
        ),
        int(interval_minutes),
        int(older_than_days),
        int(batch_size),
    )
    while True:
        run_once(older_than_days=older_than_days, batch_size=batch_size)
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune old auth action tokens")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    parser.add_argument("--interval-minutes", type=int, default=None)
    parser.add_argument("--older-than-days", type=int, default=None)
    parser.add_argument("--batch-size", type=int, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    interval_minutes = int(args.interval_minutes) if args.interval_minutes is not None else _interval_minutes()
    older_than_days = int(args.older_than_days) if args.older_than_days is not None else _older_than_days()
    batch_size = int(args.batch_size) if args.batch_size is not None else _batch_size()

    if args.once:
        run_once(older_than_days=older_than_days, batch_size=batch_size)
        return
    run_forever(
        interval_minutes=interval_minutes,
        older_than_days=older_than_days,
        batch_size=batch_size,
    )


if __name__ == "__main__":
    main()


