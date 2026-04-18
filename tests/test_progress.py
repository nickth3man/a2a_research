"""Progress queue draining behavior."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

from a2a_research.models import AgentRole
from a2a_research.progress import (
    Bus,
    ProgressEvent,
    ProgressPhase,
    create_progress_reporter,
    drain_progress_while_running,
    emit,
)


@pytest.mark.asyncio
async def test_bus_register_get_unregister_lifecycle() -> None:
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    Bus.register("session-1", queue)
    assert Bus.get("session-1") is queue
    Bus.unregister("session-1")
    assert Bus.get("session-1") is None


@pytest.mark.asyncio
async def test_emit_returns_silently_when_no_queue_registered() -> None:
    emit("missing-session", ProgressPhase.STEP_STARTED, AgentRole.PLANNER, 0, 5, "planner_started")


@pytest.mark.asyncio
async def test_emit_puts_event_on_registered_queue() -> None:
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    Bus.register("session-1", queue)

    emit("session-1", ProgressPhase.STEP_STARTED, AgentRole.PLANNER, 0, 5, "planner_started")

    event = await asyncio.wait_for(queue.get(), timeout=0.5)
    assert event is not None
    assert event.session_id == "session-1"
    assert event.role == AgentRole.PLANNER

    Bus.unregister("session-1")


@pytest.mark.asyncio
async def test_drain_progress_does_not_cancel_workflow_when_queue_wins() -> None:
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    event = ProgressEvent(
        session_id="session-1",
        phase=ProgressPhase.STEP_STARTED,
        role=AgentRole.PLANNER,
        step_index=0,
        total_steps=4,
        substep_label="Researcher started.",
    )

    async def slow_workflow() -> str:
        await asyncio.sleep(0.05)
        return "done"

    workflow_task = asyncio.create_task(slow_workflow())
    await queue.put(event)

    agen = drain_progress_while_running(queue, workflow_task)
    yielded = await anext(agen)

    assert yielded == event
    assert workflow_task.cancelled() is False
    assert workflow_task.done() is False

    workflow_task.cancel()
    with suppress(asyncio.CancelledError):
        await workflow_task
    await agen.aclose()


@pytest.mark.asyncio
async def test_drain_progress_drains_trailing_events_after_workflow_done() -> None:
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    event = ProgressEvent(
        session_id="session-1",
        phase=ProgressPhase.STEP_COMPLETED,
        role=AgentRole.PLANNER,
        step_index=0,
        total_steps=4,
        substep_label="Researcher completed.",
    )

    async def finished_workflow() -> str:
        return "done"

    workflow_task = asyncio.create_task(finished_workflow())
    await workflow_task
    await queue.put(event)
    await queue.put(None)

    events = [evt async for evt in drain_progress_while_running(queue, workflow_task)]

    assert events == [event]


@pytest.mark.asyncio
async def test_create_progress_reporter_schedules_put_on_target_loop() -> None:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    reporter = create_progress_reporter(loop, queue)

    event = ProgressEvent(
        session_id="session-1",
        phase=ProgressPhase.STEP_STARTED,
        role=AgentRole.PLANNER,
        step_index=0,
        total_steps=4,
        substep_label="start",
    )

    reporter(event)
    reporter(None)

    delivered = await asyncio.wait_for(queue.get(), timeout=0.5)
    sentinel = await asyncio.wait_for(queue.get(), timeout=0.5)

    assert delivered is event
    assert sentinel is None


def test_create_progress_reporter_uses_call_soon_threadsafe() -> None:
    from unittest.mock import MagicMock

    loop = MagicMock()
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    reporter = create_progress_reporter(loop, queue)

    reporter(None)

    loop.call_soon_threadsafe.assert_called_once_with(queue.put_nowait, None)
