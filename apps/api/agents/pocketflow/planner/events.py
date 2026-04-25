"""Handoff logging and plan artifact creation for the Planner agent."""

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

    from core import Claim


async def enqueue_plan_result(
    task: Task,
    event_queue: EventQueue,
    query: str,
    claims: list[Claim],
    claim_dag: Any,
    seed_queries: list[str],
    status: TaskState,
    error_text: str | None,
    session_id: str,
    planner_step: int,
    total_steps: int,
) -> None:
    """Build the plan artifact, enqueue it, then enqueue status."""
    artifact = Artifact(
        artifact_id="plan",
        name="plan",
        parts=[
            make_data_part(
                {
                    "query": query,
                    "claims": [c.model_dump(mode="json") for c in claims],
                    "claim_dag": (
                        claim_dag.model_dump(mode="json") if claim_dag else {}
                    ),
                    "seed_queries": seed_queries,
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
        AgentRole.PLANNER,
        planner_step,
        total_steps,
        (
            "planner_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "planner_failed"
        ),
        detail=f"claims={len(claims)} seeds={len(seed_queries)}",
    )
