"""Unit tests for database startup bootstrap."""

import asyncio

from src.db import session as database_session


class FakeConnection:
    """Minimal async connection used to verify SQLAlchemy sync callbacks."""

    async def execute(self, statement) -> None:
        """Accept the bootstrap statements."""
        statement_text = str(statement)
        assert "pg_advisory_xact_lock" in statement_text or "btree_gist" in statement_text

    async def run_sync(self, callback) -> None:
        """Execute the metadata callback with a fake synchronous connection."""
        callback(object())


class FakeBegin:
    """Async context manager representing an engine transaction."""

    async def __aenter__(self) -> FakeConnection:
        """Open the fake connection."""
        return FakeConnection()

    async def __aexit__(self, *_: object) -> None:
        """Close the fake connection."""


class FakeEngine:
    """Minimal engine surface required by database initialization."""

    def begin(self) -> FakeBegin:
        """Return a fake transaction context."""
        return FakeBegin()


def test_initialize_database_creates_missing_tables(monkeypatch):
    """Startup initialization invokes metadata table creation once."""
    called = False

    def create_all(_: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(database_session, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(database_session.Base.metadata, "create_all", create_all)

    asyncio.run(database_session.initialize_database())

    assert called
