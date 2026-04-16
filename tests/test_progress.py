"""Progress queue draining behavior."""

from __future__ import annotations

import asyncio
from contextlib import suppress

import pytest

from a2a_research.models import AgentRole
from a2a_research.progress import ProgressEvent, ProgressPhase, drain_progress_while_running


@pytest.mark.asyncio
async def test_drain_progress_does_not_cancel_workflow_when_queue_wins() -> None:
    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    event = ProgressEvent(
        phase=ProgressPhase.STEP_STARTED,
        role=AgentRole.RESEARCHER,
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
        phase=ProgressPhase.STEP_COMPLETED,
        role=AgentRole.RESEARCHER,
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
