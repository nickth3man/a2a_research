"""Progress events and queue helpers for real-time UI updates."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from time import perf_counter
from typing import TYPE_CHECKING, Any

from a2a_research.app_logging import get_logger, log_event

if TYPE_CHECKING:
    from a2a_research.models import AgentRole

logger = get_logger(__name__)


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
    log_event(logger, 20, "progress.reporter.created", loop_id=id(loop), queue_id=id(queue))

    def report(event: ProgressEvent | None) -> None:
        log_event(
            logger,
            20,
            "progress.reporter.emit",
            queue_id=id(queue),
            progress=None
            if event is None
            else {
                "phase": event.phase,
                "role": event.role,
                "step_index": event.step_index,
                "total_steps": event.total_steps,
                "substep_label": event.substep_label,
                "substep_index": event.substep_index,
                "substep_total": event.substep_total,
                "detail": event.detail,
                "elapsed_ms": event.elapsed_ms,
            },
        )
        loop.call_soon_threadsafe(queue.put_nowait, event)

    return report


async def drain_progress_while_running(
    queue: ProgressQueue,
    workflow_task: asyncio.Task[Any],
) -> AsyncGenerator[ProgressEvent, None]:
    """Yield queued events until the workflow finishes and the queue is drained."""
    log_event(
        logger,
        20,
        "progress.drain.start",
        queue_id=id(queue),
        workflow_task_id=id(workflow_task),
    )

    while True:
        queue_task = asyncio.create_task(queue.get())
        done, pending = await asyncio.wait(
            {queue_task, workflow_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if workflow_task in done and queue_task in pending:
            queue_task.cancel()
            await asyncio.gather(queue_task, return_exceptions=True)

        if queue_task in done:
            event = queue_task.result()
            if event is None:
                log_event(logger, 20, "progress.drain.stop.sentinel", queue_id=id(queue))
                break
            log_event(
                logger,
                20,
                "progress.drain.yield",
                queue_id=id(queue),
                phase=event.phase,
                role=event.role,
                step_index=event.step_index,
                substep_index=event.substep_index,
            )
            yield event

        if workflow_task in done:
            log_event(
                logger,
                20,
                "progress.drain.workflow_done",
                queue_id=id(queue),
                workflow_task_id=id(workflow_task),
            )
            try:
                workflow_task.result()
            except asyncio.CancelledError:
                log_event(
                    logger,
                    20,
                    "progress.drain.workflow_cancelled",
                    queue_id=id(queue),
                    workflow_task_id=id(workflow_task),
                )
                return
            while True:
                try:
                    event = queue.get_nowait()
                except asyncio.QueueEmpty:
                    log_event(logger, 20, "progress.drain.queue_empty", queue_id=id(queue))
                    break
                if event is None:
                    log_event(
                        logger, 20, "progress.drain.stop.trailing_sentinel", queue_id=id(queue)
                    )
                    return
                log_event(
                    logger,
                    20,
                    "progress.drain.trailing_yield",
                    queue_id=id(queue),
                    phase=event.phase,
                    role=event.role,
                    step_index=event.step_index,
                    substep_index=event.substep_index,
                )
                yield event
            return
