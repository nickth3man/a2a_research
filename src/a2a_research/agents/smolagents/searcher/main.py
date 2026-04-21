"""A2A AgentExecutor for the Searcher role."""

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
from a2a_research.a2a.proto import make_data_part, new_agent_text_message
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.smolagents.searcher.agent import build_agent
from a2a_research.agents.smolagents.searcher.card import SEARCHER_CARD
from a2a_research.agents.smolagents.searcher.core import (
    SearcherBatchResult,
    search_queries,
)
from a2a_research.agents.smolagents.searcher.payload import (
    _coerce_str_list,
    _extract_payload,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit

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
            from a2a_research.progress import emit_handoff

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
            hits, errors, successful_providers = (
                batch.hits,
                batch.errors,
                batch.providers_successful,
            )
        except Exception as exc:
            logger.exception("Searcher crashed task_id=%s", task.id)
            hits, errors, successful_providers = (
                [],
                [f"Searcher crashed: {exc}"],
                [],
            )

        from a2a_research.agents.smolagents.searcher.core import _derive_status

        status, error_text = _derive_status(
            queries, hits, errors, successful_providers
        )

        artifact = Artifact(
            artifact_id="search-hits",
            name="search-hits",
            parts=[
                make_data_part(
                    {
                        "queries_used": queries,
                        "hits": [h.model_dump(mode="json") for h in hits],
                        "errors": errors,
                        "providers_successful": successful_providers,
                    }
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
            AgentRole.SEARCHER,
            1,
            5,
            (
                "searcher_completed"
                if status == TaskState.TASK_STATE_COMPLETED
                else "searcher_failed"
            ),
            detail=f"hits={len(hits)} errors={len(errors)}",
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
