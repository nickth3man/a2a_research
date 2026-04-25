"""Artifact/status/handoff helper code for the Clarifier agent."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from core import AgentRole, ProgressPhase, emit
from core.a2a.proto import (
    make_data_part,
    new_agent_text_message,
)

if TYPE_CHECKING:
    from a2a.server.events import EventQueue
    from a2a.types import Task


async def enqueue_clarifier_result(
    task: Task,
    event_queue: EventQueue,
    result: dict[str, Any],
    status: TaskState,
    error_text: str | None,
    session_id: str,
) -> None:
    """Build the clarify artifact, enqueue it, then enqueue status."""
    artifact = Artifact(
        artifact_id="clarify",
        name="clarify",
        parts=[make_data_part(result)],
    )
    await event_queue.enqueue_event(
        TaskArtifactUpdateEvent(
            task_id=task.id,
            context_id=task.context_id,
            artifact=artifact,
            append=False,
            last_chunk=True,
        )
    )
    await event_queue.enqueue_event(
        TaskStatusUpdateEvent(
            task_id=task.id,
            context_id=task.context_id,
            status=TaskStatus(
                state=status,
                message=(
                    new_agent_text_message(error_text) if error_text else None
                ),
            ),
        )
    )
    emit(
        session_id,
        (
            ProgressPhase.STEP_COMPLETED
            if status == TaskState.TASK_STATE_COMPLETED
            else ProgressPhase.STEP_FAILED
        ),
        AgentRole.CLARIFIER,
        1,
        12,
        (
            "clarifier_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "clarifier_failed"
        ),
        detail=(
            f"disambiguations={len(result['disambiguations'])}"
            f" committed={result['committed_interpretation'][:60]}"
        ),
    )
