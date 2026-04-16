"""Progress events and queue helpers for real-time UI updates."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from time import perf_counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from a2a_research.models import AgentRole


class ProgressGranularity(IntEnum):
    """User-selectable verbosity for progress updates."""

    AGENT = 1
    SUBSTEP = 2
    DETAIL = 3


class ProgressPhase(StrEnum):
    """Discrete workflow progress event phases."""

    STEP_STARTED = "step_started"
    STEP_SUBSTEP = "step_substep"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"


@dataclass(frozen=True)
class ProgressEvent:
    """Single progress update emitted by the workflow."""

    phase: ProgressPhase
    role: AgentRole
    step_index: int
    total_steps: int
    substep_label: str
    substep_index: int = 0
    substep_total: int = 1
    granularity: ProgressGranularity = ProgressGranularity.AGENT
    detail: str = ""
    elapsed_ms: float | None = None
    created_at: float = field(default_factory=perf_counter)


ProgressQueue = asyncio.Queue[ProgressEvent | None]
ProgressReporter = Callable[[ProgressEvent | None], None]


def create_progress_reporter(
    loop: asyncio.AbstractEventLoop,
    queue: ProgressQueue,
) -> ProgressReporter:
    """Create a thread-safe reporter for worker-thread agent execution."""

    def report(event: ProgressEvent | None) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, event)

    return report


async def drain_progress_while_running(
    queue: ProgressQueue,
    workflow_task: asyncio.Task[Any],
) -> AsyncGenerator[ProgressEvent, None]:
    """Yield queued events until the workflow finishes and the queue is drained."""

    while True:
        queue_task = asyncio.create_task(queue.get())
        done, pending = await asyncio.wait(
            {queue_task, workflow_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()

        if queue_task in done:
            event = queue_task.result()
            if event is None:
                break
            yield event

        if workflow_task in done:
            workflow_task.result()
            while True:
                try:
                    event = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if event is None:
                    return
                yield event
            return
