"""Schedule repository aggregation tests."""

import asyncio
from uuid import uuid4

from src.repositories.catalog import CatalogRepository


def test_count_active_bookings_for_schedules_combines_bookings_and_holds():
    schedule_with_both = uuid4()
    schedule_with_booking = uuid4()

    class Session:
        def __init__(self):
            self.results = [[(schedule_with_both, 2), (schedule_with_booking, 1)], [(schedule_with_both, 1)]]

        async def execute(self, statement):
            del statement
            return self.results.pop(0)

    repository = CatalogRepository(Session())
    result = asyncio.run(repository.count_active_bookings_for_schedules([schedule_with_both, schedule_with_booking]))

    assert result == {schedule_with_both: 3, schedule_with_booking: 1}


def test_count_active_bookings_for_no_schedules_skips_database():
    class Session:
        async def execute(self, statement):
            del statement
            raise AssertionError("Database must not be queried for an empty schedule list")

    result = asyncio.run(CatalogRepository(Session()).count_active_bookings_for_schedules([]))

    assert result == {}
