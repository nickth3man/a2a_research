"""Critic — evaluates report quality."""

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

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.proto import get_data_part, get_text_part, make_data_part
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.stubs.critic.card import CRITIC_CARD
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

logger = get_logger(__name__)

__all__ = ["CriticExecutor", "build_http_app"]


class CriticExecutor(AgentExecutor):
    async def execute(self, context, event_queue):
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")

        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.CRITIC,
            10,
            12,
            "critic_started",
        )

        # Passthrough: always pass
        result = {
            "passed": True,
            "critique": "No issues found (stub).",
            "suggested_improvements": [],
            "iteration_count": 0,
            "warnings": [],
        }

        artifact = Artifact(
            artifact_id="critique",
            name="critique",
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
            AgentRole.CRITIC,
            10,
            12,
            "critic_completed",
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
        agent_executor=CriticExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=CRITIC_CARD,
    )
    return build_starlette_http_app(
        agent_card=CRITIC_CARD, http_handler=handler
    )
