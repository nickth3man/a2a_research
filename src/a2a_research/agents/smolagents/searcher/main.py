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
from a2a.utils import new_task

from a2a_research.app_logging import get_logger
from a2a_research.tools import WebHit, web_search

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

logger = get_logger(__name__)

__all__ = ["SearcherExecutor", "search_queries"]


async def search_queries(queries: list[str]) -> tuple[list[WebHit], list[str], list[str]]:
    """Run :func:`web_search` across ``queries`` in parallel.

    Returns ``(hits, errors, providers_successful)`` where hits are deduped by
    URL, errors is the deduplicated union of per-provider failure reasons, and
    providers_successful is the union of providers that ran without error for
    at least one query.
    """
    if not queries:
        return [], [], []
    results = await asyncio.gather(*[web_search(q) for q in queries], return_exceptions=False)
    by_url: dict[str, WebHit] = {}
    errors: list[str] = []
    seen_errors: set[str] = set()
    successful_providers: set[str] = set()
    for sr in results:
        for hit in sr.hits:
            by_url.setdefault(hit.url, hit)
        for err in sr.errors:
            if err not in seen_errors:
                seen_errors.add(err)
                errors.append(err)
        successful_providers.update(sr.providers_successful)
    hits = sorted(by_url.values(), key=lambda h: (-h.score, h.source, h.url))
    logger.info(
        "Searcher searched queries=%s merged_hits=%s errors=%s successful_providers=%s",
        len(queries),
        len(hits),
        len(errors),
        sorted(successful_providers),
    )
    return hits, errors, sorted(successful_providers)


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
        task = context.current_task or new_task(context.message)  # type: ignore[arg-type]
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        queries = _coerce_str_list(payload.get("queries"))
        if not queries and isinstance(payload.get("query"), str):
            queries = [payload["query"]]

        try:
            hits, errors, successful_providers = await search_queries(queries)
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
                status=TaskStatus(state=status),
                final=True,
                metadata={"error": error_text} if error_text else None,
            )
        )

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
