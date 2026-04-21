"""A2A AgentExecutor for the Synthesizer."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import TaskState

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.pydantic_ai.synthesizer.artifacts import (
    enqueue_report_artifacts,
)
from a2a_research.agents.pydantic_ai.synthesizer.card import SYNTHESIZER_CARD
from a2a_research.agents.pydantic_ai.synthesizer.core import synthesize
from a2a_research.agents.pydantic_ai.synthesizer.payload import (
    _coerce_claims,
    _coerce_sources,
    _extract_payload,
)
from a2a_research.logging.app_logging import get_logger
from a2a_research.models import AgentRole, ReportOutput
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["SynthesizerExecutor", "build_http_app", "synthesize"]


class SynthesizerExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")
        if session_id and handoff_from:
            from a2a_research.progress import emit_handoff

            emit_handoff(
                direction="received",
                role=AgentRole.SYNTHESIZER,
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
        query = str(payload.get("query") or "")
        claims = _coerce_claims(
            payload.get("verified_claims") or payload.get("claims") or []
        )
        sources = _coerce_sources(payload.get("sources") or [])
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.SYNTHESIZER,
            4,
            5,
            "synthesizer_started",
        )

        try:
            report = await synthesize(
                query, claims, sources, session_id=session_id
            )
            status = TaskState.TASK_STATE_COMPLETED
            error_text: str | None = None
        except Exception as exc:
            logger.exception("Synthesizer failed task_id=%s", task.id)
            report = ReportOutput(
                title="Report unavailable",
                summary=f"The Synthesizer failed: {exc}",
            )
            status = TaskState.TASK_STATE_FAILED
            error_text = str(exc)

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.SYNTHESIZER,
            4,
            5,
            "rendering_markdown",
        )
        await enqueue_report_artifacts(
            task, event_queue, report, status, error_text, session_id
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=SynthesizerExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=SYNTHESIZER_CARD,
    )
    return build_starlette_http_app(
        agent_card=SYNTHESIZER_CARD, http_handler=handler
    )
