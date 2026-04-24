"""Verified-result serialization and artifact/status enqueue logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.backend.core.a2a.proto import (
    make_data_part,
    new_agent_text_message,
)
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue
    from a2a.types import Task

    from a2a_research.backend.agents.langgraph.fact_checker.state import (
        FactCheckRunResult,
    )


async def enqueue_verified_result(
    task: Task,
    event_queue: EventQueue,
    result: FactCheckRunResult,
    status: TaskState,
    error_text: str | None,
    session_id: str,
) -> None:
    """Build the verified-result artifact, enqueue it, then enqueue status."""
    artifact = Artifact(
        artifact_id="verified",
        name="verified",
        parts=[
            make_data_part(
                {
                    "verified_claims": [
                        c.model_dump(mode="json")
                        for c in result["verified_claims"]
                    ],
                    "sources": [
                        s.model_dump(mode="json") for s in result["sources"]
                    ],
                    "errors": list(result["errors"]),
                    "search_exhausted": bool(result["search_exhausted"]),
                    "rounds": result["rounds"],
                }
            )
        ],
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
        AgentRole.FACT_CHECKER,
        3,
        5,
        (
            "fact_checker_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "fact_checker_failed"
        ),
        detail=f"rounds={result['rounds']} errors={len(result['errors'])}",
    )
