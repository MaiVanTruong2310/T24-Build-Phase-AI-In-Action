import datetime

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.UTC

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db.session import get_auth_db_session
from src.main import app


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""

    # API unit tests supply their own repositories/providers. Never open a real database.
    async def mock_auth_session():
        yield AsyncMock()

    previous = app.dependency_overrides.get(get_auth_db_session)
    app.dependency_overrides.setdefault(get_auth_db_session, mock_auth_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        try:
            yield ac
        finally:
            if previous is None:
                app.dependency_overrides.pop(get_auth_db_session, None)
            else:
                app.dependency_overrides[get_auth_db_session] = previous


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
