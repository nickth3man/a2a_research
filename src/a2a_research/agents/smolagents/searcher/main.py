"""A2A AgentExecutor for the Searcher role.

Consumes ``{queries: list[str]}`` and returns a Task with a DataArtifact of
``{queries_used, hits, errors, providers_successful}``.

Error handling:
- If every provider fails for every query (no hits + at least one error): emit
  ``TaskState.failed`` with the provider-level failure reasons so the
  FactChecker can see exactly why the web was unavailable.
- If some providers succeed (even with zero results): emit ``completed`` and
  attach any partial errors so downstream can log / annotate them.

The Searcher is also wired as a smolagents :class:`ToolCallingAgent` (see
``.agent``) for the standalone demo, but the pipeline path calls
:func:`a2a_research.tools.web_search` directly in parallel for predictable
latency and straightforward error accounting.
"""

from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING, Any, cast

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
from a2a.utils import new_agent_text_message
from pydantic import BaseModel, Field

from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.smolagents.searcher.agent import build_agent
from a2a_research.agents.smolagents.searcher.card import SEARCHER_CARD
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import AgentRole
from a2a_research.progress import ProgressPhase, emit
from a2a_research.tools import WebHit

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["SearcherBatchResult", "SearcherExecutor", "build_http_app", "search_queries"]


class SearcherBatchResult(BaseModel):
    hits: list[WebHit] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    providers_successful: list[str] = Field(default_factory=list)


async def search_queries(queries: list[str], *, session_id: str = "") -> SearcherBatchResult:
    """Run the smolagents Searcher tool-calling loop for ``queries``."""
    if not queries:
        return SearcherBatchResult()

    prompt = (
        "Queries to search:\n"
        + "\n".join(f"- {query}" for query in queries)
        + "\n\nReturn JSON only with keys queries_used and hits."
    )

    agent = build_agent()
    runner = cast("Any", agent.run)
    raw_output = await asyncio.to_thread(runner, prompt)
    data = parse_json_safely(str(raw_output))
    by_url: dict[str, WebHit] = {}
    errors: list[str] = []
    seen_errors: set[str] = set()
    successful_providers: set[str] = set()

    raw_hits_any = data.get("hits")
    raw_hits: list[object] = raw_hits_any if isinstance(raw_hits_any, list) else []
    for raw_hit in raw_hits:
        if not isinstance(raw_hit, dict):
            continue
        hit = WebHit.model_validate(raw_hit)
        by_url.setdefault(hit.url, hit)
        successful_providers.add(hit.source)

    raw_errors_any = data.get("errors")
    raw_errors: list[object] = raw_errors_any if isinstance(raw_errors_any, list) else []
    for err in raw_errors:
        if isinstance(err, str) and err not in seen_errors:
            seen_errors.add(err)
            errors.append(err)

    queries_used_raw = data.get("queries_used") or queries
    queries_used = (
        [item.strip() for item in queries_used_raw if isinstance(item, str) and item.strip()]
        if isinstance(queries_used_raw, list)
        else queries
    )
    if not by_url and not errors:
        errors.append("Searcher agent returned no usable hits.")

    for index, query in enumerate(queries_used, start=1):
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.SEARCHER,
            1,
            5,
            f"search_query_{index}",
            substep_index=index,
            substep_total=max(len(queries_used), 1),
            detail=f"query={query[:80]} providers={','.join(sorted(successful_providers)) or 'none'}",
        )
    hits = sorted(by_url.values(), key=lambda h: (-h.score, h.source, h.url))
    logger.info(
        "Searcher searched queries=%s merged_hits=%s errors=%s successful_providers=%s",
        len(queries),
        len(hits),
        len(errors),
        sorted(successful_providers),
    )
    return SearcherBatchResult(
        hits=hits,
        errors=errors,
        providers_successful=sorted(successful_providers),
    )


def _derive_status(
    queries: list[str],
    hits: list[WebHit],
    errors: list[str],
    successful_providers: list[str],
) -> tuple[TaskState, str | None]:
    if not queries:
        return TaskState.completed, None
    # All providers errored for every query → the web layer is unavailable.
    if not successful_providers and errors:
        return TaskState.failed, ("All web-search providers failed: " + " | ".join(errors))
    # Providers ran but the query simply had no matches: still a valid outcome.
    return TaskState.completed, None


class SearcherExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        session_id = str(payload.get("session_id") or "")
        queries = _coerce_str_list(payload.get("queries"))
        query_raw = payload.get("query")
        if not queries and isinstance(query_raw, str):
            queries = [query_raw]
        emit(session_id, ProgressPhase.STEP_STARTED, AgentRole.SEARCHER, 1, 5, "searcher_started")

        try:
            batch = await search_queries(queries, session_id=session_id)
            hits, errors, successful_providers = (
                batch.hits,
                batch.errors,
                batch.providers_successful,
            )
        except Exception as exc:
            logger.exception("Searcher crashed task_id=%s", task.id)
            hits, errors, successful_providers = [], [f"Searcher crashed: {exc}"], []

        status, error_text = _derive_status(queries, hits, errors, successful_providers)

        artifact = Artifact(
            artifact_id="search-hits",
            name="search-hits",
            parts=[
                Part(
                    root=DataPart(
                        data={
                            "queries_used": queries,
                            "hits": [h.model_dump(mode="json") for h in hits],
                            "errors": errors,
                            "providers_successful": successful_providers,
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
                status=TaskStatus(
                    state=status,
                    message=new_agent_text_message(error_text) if error_text else None,
                ),
                final=True,
            )
        )
        emit(
            session_id,
            ProgressPhase.STEP_COMPLETED
            if status == TaskState.completed
            else ProgressPhase.STEP_FAILED,
            AgentRole.SEARCHER,
            1,
            5,
            "searcher_completed" if status == TaskState.completed else "searcher_failed",
            detail=f"hits={len(hits)} errors={len(errors)}",
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        pass


def _extract_payload(context: RequestContext) -> dict[str, object]:
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
                return dict(data)
    return {}


def _coerce_str_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []


def build_http_app() -> Any:
    handler = DefaultRequestHandler(
        agent_executor=SearcherExecutor(), task_store=InMemoryTaskStore()
    )
    return A2AStarletteApplication(agent_card=SEARCHER_CARD, http_handler=handler).build()
