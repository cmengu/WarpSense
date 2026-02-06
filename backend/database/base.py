"""
This folder sets up the bridge between your Python code (Pydantic models) and the database, ensures the schema is defined, connections are established, and everything works before production.
SQLAlchemy declarative base.
Blueprint for all tables
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""

