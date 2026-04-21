"""A2A AgentExecutor for the FactChecker role."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import TaskState

from a2a_research.a2a.compat import build_http_app as build_starlette_http_app
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.langgraph.fact_checker.card import FACT_CHECKER_CARD
from a2a_research.agents.langgraph.fact_checker.core import run_fact_check
from a2a_research.agents.langgraph.fact_checker.payload import (
    _coerce_claims,
    _coerce_pages,
    _coerce_sources,
    _extract_payload,
)
from a2a_research.agents.langgraph.fact_checker.result import (
    enqueue_verified_result,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

    from a2a_research.agents.langgraph.fact_checker.state import (
        FactCheckRunResult,
    )

logger = get_logger(__name__)
__all__ = ["FactCheckerExecutor", "build_http_app", "run_fact_check"]


class FactCheckerExecutor(AgentExecutor):
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
                role=AgentRole.FACT_CHECKER,
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
        claims = _coerce_claims(payload.get("claims") or [])
        evidence = _coerce_pages(payload.get("evidence") or [])
        sources = _coerce_sources(payload.get("sources") or [])
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.FACT_CHECKER,
            3,
            5,
            "fact_checker_started",
        )

        try:
            result: FactCheckRunResult = await run_fact_check(
                query,
                claims,
                evidence,
                sources,
                session_id=session_id,
            )
            error_text: str | None = None
            status = TaskState.TASK_STATE_COMPLETED
        except Exception as exc:
            logger.exception("FactChecker crashed task_id=%s", task.id)
            result = {
                "verified_claims": claims,
                "sources": sources,
                "errors": [f"FactChecker crashed: {exc}"],
                "search_exhausted": True,
                "rounds": 0,
            }
            status = TaskState.TASK_STATE_FAILED
            error_text = str(exc)

        await enqueue_verified_result(
            task, event_queue, result, status, error_text, session_id
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=FactCheckerExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=FACT_CHECKER_CARD,
    )
    return build_starlette_http_app(
        agent_card=FACT_CHECKER_CARD, http_handler=handler
    )
