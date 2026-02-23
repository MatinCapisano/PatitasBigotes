from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url and database_url.strip():
        return database_url.strip()
    raise RuntimeError("DATABASE_URL is required")


def get_mercadopago_access_token() -> str:
    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN", "").strip()
    if access_token:
        return access_token
    raise RuntimeError("MERCADOPAGO_ACCESS_TOKEN is required")


def get_mercadopago_env() -> str:
    env = os.getenv("MERCADOPAGO_ENV", "sandbox").strip().lower()
    if env not in {"sandbox", "production"}:
        raise RuntimeError("MERCADOPAGO_ENV must be 'sandbox' or 'production'")
    return env


def get_mercadopago_timeout_seconds() -> int:
    raw_timeout = os.getenv("MERCADOPAGO_TIMEOUT_SECONDS", "10").strip()
    timeout = int(raw_timeout)
    if timeout <= 0:
        raise RuntimeError("MERCADOPAGO_TIMEOUT_SECONDS must be greater than 0")
    return timeout


def get_mercadopago_success_url() -> str:
    return os.getenv(
        "MERCADOPAGO_SUCCESS_URL",
        "http://localhost:8000/payments/success",
    ).strip()


def get_mercadopago_failure_url() -> str:
    return os.getenv(
        "MERCADOPAGO_FAILURE_URL",
        "http://localhost:8000/payments/failure",
    ).strip()


def get_mercadopago_pending_url() -> str:
    return os.getenv(
        "MERCADOPAGO_PENDING_URL",
        "http://localhost:8000/payments/pending",
    ).strip()


def get_mercadopago_notification_url() -> str:
    return os.getenv(
        "MERCADOPAGO_NOTIFICATION_URL",
        "http://localhost:8000/payments/webhook/mercadopago",
    ).strip()


def get_mercadopago_webhook_token() -> str:
    return os.getenv("MERCADOPAGO_WEBHOOK_TOKEN", "").strip()


def get_mercadopago_webhook_secret() -> str:
    secret = os.getenv("MERCADOPAGO_WEBHOOK_SECRET", "").strip()
    if secret:
        return secret
    raise RuntimeError("MERCADOPAGO_WEBHOOK_SECRET is required")
