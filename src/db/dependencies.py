"""FastAPI dependencies related to persistence."""

from src.db.session import get_db_session

__all__ = ["get_db_session"]
