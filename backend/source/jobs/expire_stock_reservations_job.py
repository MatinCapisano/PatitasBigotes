from __future__ import annotations

import argparse
from datetime import UTC, datetime
import logging
import os
import time

from source.db.session import SessionLocal
from source.services.stock_reservations_s import expire_active_reservations

DEFAULT_INTERVAL_MINUTES = 180

logger = logging.getLogger("stock_reservations_job")


def _interval_minutes() -> int:
    raw = str(os.getenv("STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES", DEFAULT_INTERVAL_MINUTES)).strip()
    interval = int(raw)
    if interval <= 0:
        raise RuntimeError("STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES must be greater than 0")
    return interval


def run_once() -> int:
    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        expired = expire_active_reservations(now=now, db=db)
        db.commit()
        logger.info("event=expire_stock_reservations_run expired_count=%s", int(expired))
        return int(expired)
    except Exception:
        db.rollback()
        logger.exception("event=expire_stock_reservations_failed")
        raise
    finally:
        db.close()


def run_forever(interval_minutes: int) -> None:
    interval_seconds = int(interval_minutes) * 60
    logger.info("event=expire_stock_reservations_started interval_minutes=%s", int(interval_minutes))
    while True:
        run_once()
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
        help="Run interval in minutes (defaults to STOCK_RESERVATIONS_JOB_INTERVAL_MINUTES or 180)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    interval_minutes = int(args.interval_minutes) if args.interval_minutes is not None else _interval_minutes()
    if interval_minutes <= 0:
        raise RuntimeError("interval must be greater than 0")

    if args.once:
        run_once()
        return
    run_forever(interval_minutes=interval_minutes)


if __name__ == "__main__":
    main()


