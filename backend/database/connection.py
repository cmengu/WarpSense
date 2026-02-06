"""
This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
Database connection setup for PostgreSQL.
Set up DB connection & sessions
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .base import Base


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not set")
    return database_url


def create_engine_from_env():
    return create_engine(get_database_url(), future=True)


engine = create_engine_from_env()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
