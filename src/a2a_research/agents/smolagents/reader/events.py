"""Per-page progress emission and completion logging for the Reader agent."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.a2a.proto import make_data_part, new_agent_text_message
from a2a_research.logging.app_logging import log_event
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue
    from a2a.types import Task

    from a2a_research.tools import PageContent


def emit_page_progress(
    session_id: str,
    pages: list[PageContent],
    urls: list[str],
) -> None:
    """Emit a STEP_SUBSTEP progress event for each fetched page."""
    for index, page in enumerate(pages, start=1):
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.READER,
            2,
            5,
            f"fetch_url_{index}",
            substep_index=index,
            substep_total=max(len(urls), 1),
            detail=page.error or page.title or page.url,
        )


async def enqueue_reader_result(
    task: Task,
    event_queue: EventQueue,
    pages: list[PageContent],
    urls: list[str],
    status: TaskState,
    error_text: str | None,
    session_id: str,
) -> None:
    """Build the extracted-pages artifact, enqueue it, then enqueue status."""
    artifact = Artifact(
        artifact_id="extracted-pages",
        name="extracted-pages",
        parts=[
            make_data_part(
                {"pages": [p.model_dump(mode="json") for p in pages]}
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
        AgentRole.READER,
        2,
        5,
        (
            "reader_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "reader_failed"
        ),
        detail=f"urls={len(urls)} pages={len(pages)}",
    )


def log_reader_completion(
    logger: logging.Logger,
    task: Task,
    urls: list[str],
    pages: list[PageContent],
) -> None:
    """Log reader completion with summary."""
    log_event(
        logger,
        logging.INFO,
        "reader.task_completed",
        task_id=str(task.id),
        urls=urls,
        page_count=len(pages),
        pages_summary=[
            {
                "url": p.url,
                "ok": not bool(p.error),
                "error": p.error,
                "words": p.word_count,
            }
            for p in pages
        ],
    )
