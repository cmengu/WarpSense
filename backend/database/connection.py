"""
This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
Database connection setup for PostgreSQL.
Set up DB connection & sessions
"""

import os
from pathlib import Path

from dotenv import load_dotenv

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base


def load_env_from_backend() -> None:
    backend_dir = Path(__file__).resolve().parent.parent
    env_path = backend_dir / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def get_database_url() -> str:
    load_env_from_backend()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")
    return database_url


def create_engine_from_env():
    return create_engine(get_database_url(), future=True)


engine = create_engine_from_env()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
