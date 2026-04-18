"""A2A AgentExecutor for the Planner role.

Consumes ``{query}`` (string or DataPart) and returns a Task with a DataArtifact
of ``{claims, seed_queries}`` — the handoff shape the FactChecker expects.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
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
from a2a_research.agents.pocketflow.planner.card import PLANNER_CARD
from a2a_research.agents.pocketflow.planner.flow import plan
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["PlannerExecutor", "build_http_app"]


class PlannerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        query = _extract_query(context)
        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        emit(session_id, ProgressPhase.STEP_STARTED, AgentRole.PLANNER, 0, 5, "planner_started")
        emit(session_id, ProgressPhase.STEP_SUBSTEP, AgentRole.PLANNER, 0, 5, "decompose")

        try:
            claims, seed_queries = await plan(query)
            status = TaskState.completed
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Planner failed task_id=%s", task.id)
            claims, seed_queries = [], []
            status = TaskState.failed
            error_text = str(exc)

        artifact = Artifact(
            artifact_id="plan",
            name="plan",
            parts=[
                Part(
                    root=DataPart(
                        data={
                            "query": query,
                            "claims": [c.model_dump(mode="json") for c in claims],
                            "seed_queries": seed_queries,
                        }
                    )
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
                status=TaskStatus(state=status),
                final=True,
                metadata={"error": error_text} if error_text else None,
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED
            if status == TaskState.completed
            else ProgressPhase.STEP_FAILED,
            AgentRole.PLANNER,
            0,
            5,
            "planner_completed" if status == TaskState.completed else "planner_failed",
            detail=f"claims={len(claims)} seeds={len(seed_queries)}",
        )
        logger.info(
            "Planner task_id=%s claims=%s seeds=%s",
            task.id,
            len(claims),
            len(seed_queries),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _extract_query(context: RequestContext) -> str:
    payload = _extract_payload(context)
    query = payload.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    if context.message is None:
        return ""
    text_parts: list[str] = []
    for part in context.message.parts:
        root = getattr(part, "root", part)
        if isinstance(root, DataPart):
            query = root.data.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        elif isinstance(root, TextPart) and root.text.strip():
            text_parts.append(root.text.strip())
    joined = "\n".join(text_parts).strip()
    try:
        data = json.loads(joined) if joined else None
    except (ValueError, TypeError):
        data = None
    if isinstance(data, dict) and isinstance(data.get("query"), str):
        return str(data["query"]).strip()
    return joined


def _extract_payload(context: RequestContext) -> dict[str, object]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        root = getattr(part, "root", part)
        if isinstance(root, DataPart):
            return dict(root.data)
    return {}


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=PlannerExecutor(), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=PLANNER_CARD, http_handler=handler).build()
