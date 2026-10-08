import datetime

if not hasattr(datetime, "UTC"):
    datetime.UTC = datetime.UTC

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.db.dependencies import get_auth_db_session, get_db_session
from src.main import app


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""

    # API unit tests supply their own repositories/providers. Never open a real database.
    async def mock_db_session():
        yield AsyncMock()

    dependencies = (get_db_session, get_auth_db_session)
    missing = object()
    previous = {dependency: app.dependency_overrides.get(dependency, missing) for dependency in dependencies}
    for dependency in dependencies:
        app.dependency_overrides.setdefault(dependency, mock_db_session)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        try:
            yield ac
        finally:
            for dependency, override in previous.items():
                if override is missing:
                    app.dependency_overrides.pop(dependency, None)
                else:
                    app.dependency_overrides[dependency] = override


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
