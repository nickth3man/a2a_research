"""A2A AgentExecutor for the Clarifier role.

Consumes ``{query, query_class}`` and returns a Task with a DataArtifact
of ``{disambiguations, committed_interpretation, audit_note}``.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

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
from a2a_research.a2a.proto import (
    get_data_part,
    get_text_part,
    make_data_part,
    new_agent_text_message,
)
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.pocketflow.clarifier.card import CLARIFIER_CARD
from a2a_research.agents.pocketflow.clarifier.flow import clarify
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit, using_session

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["ClarifierExecutor", "build_http_app"]


class ClarifierExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        query = _extract_query(context, payload)
        query_class = (
            str(payload.get("query_class") or "factual").strip().lower()
        )
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")

        if session_id and handoff_from:
            from a2a_research.progress import emit_handoff

            emit_handoff(
                direction="received",
                role=AgentRole.CLARIFIER,
                peer_role=str(handoff_from),
                payload_keys=sorted(payload.keys()),
                payload_bytes=len(
                    json.dumps(payload, default=str).encode("utf-8")
                ),
                payload_preview=json.dumps(
                    payload, default=str, indent=2, sort_keys=True
                ),
                session_id=session_id,
            )

        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.CLARIFIER,
            1,
            12,
            "clarifier_started",
        )
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.CLARIFIER,
            1,
            12,
            "disambiguate",
        )

        try:
            with using_session(session_id):
                result = await clarify(
                    query, query_class=query_class, session_id=session_id
                )
            status = TaskState.TASK_STATE_COMPLETED
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Clarifier failed task_id=%s", task.id)
            result = {
                "disambiguations": [],
                "committed_interpretation": query,
                "audit_note": f"Clarifier error: {exc}",
            }
            status = TaskState.TASK_STATE_FAILED
            error_text = str(exc)

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
                        new_agent_text_message(error_text)
                        if error_text
                        else None
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
        logger.info(
            "Clarifier task_id=%s disambiguations=%s committed=%r",
            task.id,
            len(result["disambiguations"]),
            result["committed_interpretation"],
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def _extract_query(context: RequestContext, payload: dict[str, Any]) -> str:
    query = payload.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    if context.message is None:
        return ""
    text_parts: list[str] = []
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            query = data_part.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        text_part = get_text_part(part)
        if text_part and text_part.strip():
            text_parts.append(text_part.strip())
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
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
    return {}


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=ClarifierExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=CLARIFIER_CARD,
    )
    return build_starlette_http_app(
        agent_card=CLARIFIER_CARD, http_handler=handler
    )
