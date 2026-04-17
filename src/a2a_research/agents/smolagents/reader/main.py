"""A2A AgentExecutor for the Reader role.

Consumes ``{urls: list[str]}`` and returns a Task with a DataArtifact of
``{pages: [PageContent, …]}``. Pages that fail to fetch are included with
``error != None`` so the FactChecker can distinguish "no evidence" from
"evidence retrieved but empty".
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    Artifact,
    DataPart,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.app_logging import get_logger
from a2a_research.tools import fetch_many

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["ReaderExecutor"]


class ReaderExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        urls = _coerce_str_list(payload.get("urls") or payload.get("url"))
        max_chars = int(payload.get("max_chars") or 8000)

        try:
            pages = await fetch_many(urls, max_chars=max_chars) if urls else []
            status = TaskState.completed
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Reader failed task_id=%s", task.id)
            pages = []
            status = TaskState.failed
            error_text = str(exc)

        artifact = Artifact(
            artifact_id="extracted-pages",
            name="extracted-pages",
            parts=[
                Part(root=DataPart(data={"pages": [p.model_dump(mode="json") for p in pages]}))
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
                status=TaskStatus(state=status),
                final=True,
                metadata={"error": error_text} if error_text else None,
            )
        )
        logger.info("Reader task_id=%s urls=%s pages=%s", task.id, len(urls), len(pages))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        root = getattr(part, "root", part)
        if isinstance(root, DataPart):
            return dict(root.data)
        if isinstance(root, TextPart):
            try:
                data = json.loads(root.text)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return {}


def _coerce_str_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []
