"""Alembic integration point for SQLAlchemy metadata.

An Alembic ``env.py`` can import ``target_metadata`` when migrations are
introduced at the repository root.
"""

from src.db.base import Base

target_metadata = Base.metadata
