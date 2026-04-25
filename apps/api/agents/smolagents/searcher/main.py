"""A2A AgentExecutor for the Searcher role."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore

from agents.smolagents.searcher.card import SEARCHER_CARD
from agents.smolagents.searcher.core import (
    SearcherBatchResult,
    search_queries,
)
from agents.smolagents.searcher.payload import (
    _coerce_str_list,
    _extract_payload,
)
from agents.smolagents.searcher.result import (
    enqueue_search_result,
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

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = [
    "SearcherBatchResult",
    "SearcherExecutor",
    "build_http_app",
    "search_queries",
]


class SearcherExecutor(AgentExecutor):
    async def execute(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        handoff_from = payload.get("handoff_from")
        if session_id and handoff_from:
            from core import emit_handoff

            emit_handoff(
                direction="received",
                role=AgentRole.SEARCHER,
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
        queries = _coerce_str_list(payload.get("queries"))
        query_raw = payload.get("query")
        if not queries and isinstance(query_raw, str):
            queries = [query_raw]
        emit(
            session_id,
            ProgressPhase.STEP_STARTED,
            AgentRole.SEARCHER,
            1,
            5,
            "searcher_started",
        )

        try:
            batch = await search_queries(queries, session_id=session_id)
        except Exception as exc:
            logger.exception("Searcher crashed task_id=%s", task.id)
            batch = SearcherBatchResult(
                hits=[],
                errors=[f"Searcher crashed: {exc}"],
                providers_successful=[],
            )

        await enqueue_search_result(
            task, event_queue, queries, batch, session_id
        )

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        pass


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=SearcherExecutor(),
        task_store=InMemoryTaskStore(),
        agent_card=SEARCHER_CARD,
    )
    return build_starlette_http_app(
        agent_card=SEARCHER_CARD, http_handler=handler
    )
