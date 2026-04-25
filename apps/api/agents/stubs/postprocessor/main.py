"""Postprocessor — renders citations, redacts PII, formats outputs."""

from __future__ import annotations

import json
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    Artifact,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from agents.stubs.postprocessor.card import (
    POSTPROCESSOR_CARD,
)
from core import (
    AgentRole,
    ProgressPhase,
    emit,
    get_logger,
    initial_task_or_new,
)
from core.a2a.compat import (
    build_http_app as build_starlette_http_app,
)
from core.a2a.proto import (
    get_data_part,
    get_text_part,
    make_data_part,
)

logger = get_logger(__name__)

__all__ = ["PostprocessorExecutor", "build_http_app"]


class PostprocessorExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        report = payload.get("report", {})
        session_id = str(payload.get("session_id") or "")

        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.POSTPROCESSOR,
            11,
            12,
            "postprocessor_started",
        )

        # Passthrough: format report as markdown
        if isinstance(report, dict):
            title = report.get("title", "Research Report")
            summary = report.get("summary", "")
            sections = report.get("sections", [])
            md_lines = [f"# {title}", "", summary, ""]
            for sec in sections:
                if isinstance(sec, dict):
                    md_lines.append(f"## {sec.get('heading', '')}")
                    md_lines.append("")
                    md_lines.append(sec.get("body", ""))
                    md_lines.append("")
            markdown = "\n".join(md_lines)
        else:
            markdown = str(report)

        result = {
            "formatted_outputs": {
                "markdown": markdown,
                "json": (
                    json.dumps(report)
                    if isinstance(report, dict)
                    else str(report)
                ),
            }
        }

        artifact = Artifact(
            artifact_id="postprocess",
            name="postprocess",
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
                status=TaskStatus(state=TaskState.TASK_STATE_COMPLETED),
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED,
            AgentRole.POSTPROCESSOR,
            11,
            12,
            "postprocessor_completed",
        )

    async def cancel(self, context, event_queue):
        pass


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
        text_part = get_text_part(part)
        if text_part:
            try:
                data = json.loads(text_part)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return {}


def build_http_app():
    handler = DefaultRequestHandler(
        agent_executor=PostprocessorExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=POSTPROCESSOR_CARD,
    )
    return build_starlette_http_app(
        agent_card=POSTPROCESSOR_CARD, http_handler=handler
    )
