"""Markdown/data artifact creation and enqueue loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from a2a_research.a2a.proto import (
    make_data_part,
    make_text_part,
    new_agent_text_message,
)
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue
    from a2a.types import Task

    from a2a_research.models import ReportOutput


async def enqueue_report_artifacts(
    task: Task,
    event_queue: EventQueue,
    report: ReportOutput,
    status: TaskState,
    error_text: str | None,
    session_id: str,
) -> None:
    """Build data + markdown artifacts, enqueue them, then enqueue status."""
    markdown = report.to_markdown()
    data_artifact = Artifact(
        artifact_id="report",
        name="report",
        parts=[make_data_part({"report": report.model_dump(mode="json")})],
    )
    text_artifact = Artifact(
        artifact_id="report-markdown",
        name="report-markdown",
        parts=[make_text_part(markdown)],
    )
    for artifact in (data_artifact, text_artifact):
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
        AgentRole.SYNTHESIZER,
        4,
        5,
        (
            "synthesizer_completed"
            if status == TaskState.TASK_STATE_COMPLETED
            else "synthesizer_failed"
        ),
        detail=f"report_title={report.title}",
    )
