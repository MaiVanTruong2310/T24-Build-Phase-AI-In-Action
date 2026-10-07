"""Deletion integration checks use an isolated disposable PostgreSQL schema."""
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from src.services.chat_history import ChatHistoryService, graph_thread


@pytest_asyncio.fixture
async def archive_db():
    url = os.getenv('WORKBENCH_TEST_DATABASE_URL')
    if not url:
        pytest.skip('Set WORKBENCH_TEST_DATABASE_URL for isolated PostgreSQL integration tests.')
    if url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    engine = create_async_engine(url)
    schema = 'chat_delete_test_' + uuid4().hex
    async with engine.begin() as conn:
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'''CREATE TABLE "{schema}".chat_conversations (
            id uuid PRIMARY KEY, user_id uuid NOT NULL, session_id varchar(200) NOT NULL,
            busy_until timestamptz, UNIQUE(user_id, session_id))'''))
        await conn.execute(text(f'''CREATE TABLE "{schema}".chat_turns (
            id uuid PRIMARY KEY, conversation_id uuid REFERENCES "{schema}".chat_conversations(id) ON DELETE CASCADE,
            user_text text)'''))
    # Translate only archive table names so production public tables are never touched.
    class ScopedSession:
        def __init__(self, session): self.session = session
        def begin(self): return self.session.begin()
        async def execute(self, statement, params=None):
            sql = str(statement).replace('public.chat_conversations', f'"{schema}".chat_conversations')
            return await self.session.execute(text(sql), params)
    try:
        async with async_sessionmaker(engine)() as session:
            yield session, ScopedSession(session), schema
    finally:
        async with engine.begin() as conn:
            await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        await engine.dispose()


async def seed(db, schema, user, session_id, busy=False):
    cid = uuid4()
    async with db.begin():
        await db.execute(text(f'''INSERT INTO "{schema}".chat_conversations
            VALUES (:cid,:uid,:sid,CASE WHEN :busy THEN now()+interval '5 minutes' ELSE NULL END)'''),
            {'cid': cid, 'uid': user.id, 'sid': session_id, 'busy': busy})
        await db.execute(text(f'INSERT INTO "{schema}".chat_turns VALUES (:id,:cid,:body)'),
            {'id': uuid4(), 'cid': cid, 'body': 'Private chat'})
    return cid


@pytest.mark.asyncio
async def test_delete_owned_chat_cascades_turns_and_clears_graph(archive_db):
    from src.medical_assistant.agent.graph import agent
    db, scoped, schema = archive_db
    user = SimpleNamespace(id=uuid4())
    sid = 'same-session'
    await seed(db, schema, user, sid)
    other = SimpleNamespace(id=uuid4())
    await seed(db, schema, other, sid)
    config = {'configurable': {'thread_id': graph_thread(sid, user)}}
    await agent.aupdate_state(config, {'messages': [{'role': 'user', 'content': 'Private chat'}]}, as_node='respond')
    assert (await agent.aget_state(config)).values
    await ChatHistoryService(scoped).delete_conversation(user, sid)
    assert not (await agent.aget_state(config)).values
    async with db.begin():
        assert (await db.execute(text(f'SELECT count(*) FROM "{schema}".chat_turns'))).scalar_one() == 1
        assert (await db.execute(text(f'SELECT user_id FROM "{schema}".chat_conversations'))).scalar_one() == other.id
    with pytest.raises(HTTPException) as missing:
        await ChatHistoryService(scoped).delete_conversation(user, sid)
    assert missing.value.status_code == 404


@pytest.mark.asyncio
async def test_foreign_and_busy_chats_are_preserved(archive_db):
    db, scoped, schema = archive_db
    owner = SimpleNamespace(id=uuid4())
    await seed(db, schema, owner, 'busy', busy=True)
    with pytest.raises(HTTPException) as forbidden:
        await ChatHistoryService(scoped).delete_conversation(SimpleNamespace(id=uuid4()), 'busy')
    assert forbidden.value.status_code == 404
    with pytest.raises(HTTPException) as busy:
        await ChatHistoryService(scoped).delete_conversation(owner, 'busy')
    assert busy.value.status_code == 409
    async with db.begin():
        assert (await db.execute(text(f'SELECT count(*) FROM "{schema}".chat_turns'))).scalar_one() == 1


@pytest.mark.asyncio
async def test_delete_api_requires_auth_and_uses_verified_owner(archive_db):
    from src.medical_assistant.api.routes import router
    from src.api.dependencies import get_current_user
    from src.db.dependencies import get_auth_db_session
    db, scoped, schema = archive_db
    owner = SimpleNamespace(id=uuid4())
    await seed(db, schema, owner, 'api-session')
    app = FastAPI()
    app.include_router(router, prefix='/api/v1')
    app.dependency_overrides[get_auth_db_session] = lambda: scoped
    async def unauthenticated(): raise HTTPException(401, 'Login required')
    app.dependency_overrides[get_current_user] = unauthenticated
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as client:
        assert (await client.delete('/api/v1/chat/conversations/api-session')).status_code == 401
        app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(id=uuid4())
        assert (await client.delete('/api/v1/chat/conversations/api-session')).status_code == 404
        app.dependency_overrides[get_current_user] = lambda: owner
        result = await client.delete('/api/v1/chat/conversations/api-session')
        assert result.status_code == 200 and result.json() == {'deleted': True}
