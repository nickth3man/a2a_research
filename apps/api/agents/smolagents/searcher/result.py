"""Artifact payload construction and status/error selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    from agents.smolagents.searcher.core import (
        SearcherBatchResult,
    )


async def enqueue_search_result(
    task: Task,
    event_queue: EventQueue,
    queries: list[str],
    batch: SearcherBatchResult,
    session_id: str,
) -> None:
    """Build search-hits artifact, enqueue it, then enqueue status + emit."""
    hits, errors, successful_providers = (
        batch.hits,
        batch.errors,
        batch.providers_successful,
    )

    from agents.smolagents.searcher.core import (
        _derive_status,
    )

    status, error_text = _derive_status(
        queries, hits, errors, successful_providers
    )

    artifact = Artifact(
        artifact_id="search-hits",
        name="search-hits",
        parts=[
            make_data_part(
                {
                    "queries_used": queries,
                    "hits": [h.model_dump(mode="json") for h in hits],
                    "errors": errors,
                    "providers_successful": successful_providers,
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
        AgentRole.SEARCHER,
        1,
        5,
        (
            "searcher_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "searcher_failed"
        ),
        detail=f"hits={len(hits)} errors={len(errors)}",
    )
