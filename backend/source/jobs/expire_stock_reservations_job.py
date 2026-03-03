from __future__ import annotations

import argparse
from datetime import UTC, datetime
import logging
import os
import time

from source.db.session import SessionLocal
from source.services.stock_reservations_s import expire_active_reservations

DEFAULT_INTERVAL_MINUTES = 60
DEFAULT_BATCH_LIMIT = 200
DEFAULT_MAX_BATCHES = 20

logger = logging.getLogger("stock_reservations_job")


def _interval_minutes() -> int:
    raw = str(os.getenv("STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES)).strip()
    interval = int(raw)
    if interval <= 0:
        raise RuntimeError("STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES must be greater than 0")
    return interval


def _batch_limit() -> int:
    raw = str(os.getenv("STOCK_RESERVATIONS_JOB_BATCH_LIMIT", DEFAULT_BATCH_LIMIT)).strip()
    value = int(raw)
    if value <= 0:
        raise RuntimeError("STOCK_RESERVATIONS_JOB_BATCH_LIMIT must be greater than 0")
    return value


def _max_batches() -> int:
    raw = str(os.getenv("STOCK_RESERVATIONS_JOB_MAX_BATCHES", DEFAULT_MAX_BATCHES)).strip()
    value = int(raw)
    if value <= 0:
        raise RuntimeError("STOCK_RESERVATIONS_JOB_MAX_BATCHES must be greater than 0")
    return value


def run_once(*, batch_limit: int, max_batches: int) -> int:
    db = SessionLocal()
    try:
        started_at = time.monotonic()
        processed_total = 0
        batches = 0
        for _ in range(max(1, int(max_batches))):
            now = datetime.now(UTC)
            expired = int(expire_active_reservations(now=now, db=db, limit=int(batch_limit)))
            db.commit()
            batches += 1
            processed_total += expired
            if expired == 0:
                break
        duration_ms = int((time.monotonic() - started_at) * 1000)
        logger.info(
            "event=expire_stock_reservations_run processed_total=%s batches=%s batch_limit=%s max_batches=%s duration_ms=%s",
            int(processed_total),
            int(batches),
            int(batch_limit),
            int(max_batches),
            int(duration_ms),
        )
        return int(processed_total)
    except Exception:
        db.rollback()
        logger.exception("event=expire_stock_reservations_failed")
        raise
    finally:
        db.close()


def run_forever(*, interval_minutes: int, batch_limit: int, max_batches: int) -> None:
    interval_seconds = int(interval_minutes) * 60
    logger.info(
        "event=expire_stock_reservations_started interval_minutes=%s batch_limit=%s max_batches=%s",
        int(interval_minutes),
        int(batch_limit),
        int(max_batches),
    )
    while True:
        run_once(batch_limit=batch_limit, max_batches=max_batches)
        time.sleep(interval_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Expire stock reservations periodically")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run expiration once and exit",
    )
    parser.add_argument(
        "--interval-minutes",
        type=int,
        default=None,
        help="Run interval in minutes (defaults to STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES or 60)",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=None,
        help="Reservations to process per batch (defaults to STOCK_RESERVATIONS_JOB_BATCH_LIMIT or 200)",
    )
    parser.add_argument(
        "--max-batches",
        type=int,
        default=None,
        help="Maximum batches per run (defaults to STOCK_RESERVATIONS_JOB_MAX_BATCHES or 20)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    interval_minutes = int(args.interval_minutes) if args.interval_minutes is not None else _interval_minutes()
    batch_limit = int(args.batch_limit) if args.batch_limit is not None else _batch_limit()
    max_batches = int(args.max_batches) if args.max_batches is not None else _max_batches()
    if interval_minutes <= 0:
        raise RuntimeError("interval must be greater than 0")
    if batch_limit <= 0:
        raise RuntimeError("batch_limit must be greater than 0")
    if max_batches <= 0:
        raise RuntimeError("max_batches must be greater than 0")

    if args.once:
        run_once(batch_limit=batch_limit, max_batches=max_batches)
        return
    run_forever(
        interval_minutes=interval_minutes,
        batch_limit=batch_limit,
        max_batches=max_batches,
    )


if __name__ == "__main__":
    main()


