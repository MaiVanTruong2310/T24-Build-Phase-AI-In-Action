import asyncio

import pytest

from src.medical_assistant.infrastructure.llm import FailoverChatModel, _StructuredFailover


class Provider:
    def __init__(self, delay=0, result="valid", error=None):
        self.delay = delay
        self.result = result
        self.error = error
        self.calls = 0
        self.cancelled = False

    async def ainvoke(self, *args, **kwargs):
        self.calls += 1
        try:
            await asyncio.sleep(self.delay)
            if self.error:
                raise self.error
            return self.result
        except asyncio.CancelledError:
            self.cancelled = True
            raise


@pytest.mark.asyncio
async def test_fast_primary_does_not_spend_on_backup():
    primary, backup = Provider(), Provider()
    model = FailoverChatModel(primary, [backup], hedge_delay_seconds=0.03, total_timeout_seconds=0.2)
    assert await model.ainvoke("test") == "valid"
    assert backup.calls == 0


@pytest.mark.asyncio
async def test_slow_primary_is_cancelled_after_valid_backup():
    primary, backup = Provider(delay=2), Provider(result="backup")
    model = FailoverChatModel(primary, [backup], hedge_delay_seconds=0.01, total_timeout_seconds=0.2)
    assert await model.ainvoke("test") == "backup"
    assert primary.cancelled


@pytest.mark.asyncio
async def test_invalid_structured_backup_cannot_win():
    released = asyncio.Event()
    primary, backup = Provider(result="validated"), Provider(error=ValueError("schema invalid"))

    async def validated_after_failed_backup(*args, **kwargs):
        await released.wait()
        return "validated"

    primary.ainvoke = validated_after_failed_backup
    model = FailoverChatModel(primary, [backup], hedge_delay_seconds=0.005, total_timeout_seconds=0.2)
    mark_failed = model._mark_failed

    def release_after_failure(index, *args, **kwargs):
        mark_failed(index, *args, **kwargs)
        released.set()

    model._mark_failed = release_after_failure
    structured = _StructuredFailover(model, [primary, backup], [0, 1])
    assert await structured.ainvoke("test") == "validated"
    assert model._blocked_until[1] > 0


@pytest.mark.asyncio
async def test_shared_deadline_and_client_cancellation_cleanup():
    primary, backup = Provider(delay=2), Provider(delay=2)
    model = FailoverChatModel(primary, [backup], hedge_delay_seconds=0.005, total_timeout_seconds=0.03)
    with pytest.raises(TimeoutError):
        await model.ainvoke("test")
    assert primary.cancelled and backup.cancelled
    primary.cancelled = backup.cancelled = False
    model.total_timeout_seconds = 2
    task = asyncio.create_task(model.ainvoke("test"))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert primary.cancelled and backup.cancelled
