import re

import pytest
from sqlalchemy.dialects import postgresql

from src.repositories.user import UserRepository


@pytest.mark.asyncio
async def test_patient_search_matches_full_name_only():
    class Result:
        def scalar_one(self):
            return 0

        def scalars(self):
            return self

        def all(self):
            return []

    class Session:
        statements = []

        async def execute(self, statement):
            self.statements.append(statement)
            return Result()

    session = Session()
    await UserRepository(session).search_patients(
        query="A",
        status=None,
        gender=None,
        created_from=None,
        created_to=None,
        offset=0,
        limit=20,
    )

    statements = [str(statement.compile(dialect=postgresql.dialect())) for statement in session.statements]
    where_clauses = [re.split(r"\bwhere\b", statement, maxsplit=1, flags=re.IGNORECASE)[1] for statement in statements]
    assert len(where_clauses) == 2
    assert all("users.full_name ILIKE" in clause for clause in where_clauses)
    assert all("users.email" not in clause and "users.phone" not in clause for clause in where_clauses)
