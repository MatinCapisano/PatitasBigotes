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
