"""Operational Postgres connection. URL is composed from .env (secrets stay out of code)."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

load_dotenv()  # load .env locally; real environments inject these vars directly


def database_url() -> str:
    """Build the psycopg3 URL from POSTGRES_* env vars (same ones compose uses)."""
    user = os.environ.get("POSTGRES_USER", "tsa")
    password = os.environ.get("POSTGRES_PASSWORD", "")
    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    name = os.environ.get("POSTGRES_DB", "tsa")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{name}"


def create_db_engine() -> Engine:
    return create_engine(database_url())
