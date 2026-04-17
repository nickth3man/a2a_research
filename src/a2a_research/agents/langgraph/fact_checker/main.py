"""A2A AgentExecutor for the FactChecker role.

Consumes ``{query, claims, seed_queries}`` and emits ``{verified_claims, sources}``.
Runs the LangGraph loop using a module-level :class:`A2AClient` (shared registry).
"""

from __future__ import annotations

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
from pydantic import ValidationError

from a2a_research.a2a import A2AClient
from a2a_research.a2a.request_task import initial_task_or_new
from a2a_research.agents.langgraph.fact_checker.graph import build_fact_check_graph
from a2a_research.app_logging import get_logger
from a2a_research.models import Claim, WebSource
from a2a_research.settings import settings

if TYPE_CHECKING:
    from a2a.server.events import EventQueue

    from a2a_research.agents.langgraph.fact_checker.state import FactCheckRunResult, FactCheckState

logger = get_logger(__name__)
__all__ = ["FactCheckerExecutor", "run_fact_check"]


async def run_fact_check(
    query: str,
    claims: list[Claim],
    seed_queries: list[str],
    *,
    client: A2AClient | None = None,
    max_rounds: int | None = None,
) -> FactCheckRunResult:
    """Execute the FactChecker graph end-to-end; return ``{verified_claims, sources}``."""
    active_client = client or A2AClient()
    graph = build_fact_check_graph(active_client)
    initial_state: FactCheckState = {
        "query": query,
        "claims": list(claims),
        "evidence": [],
        "hits": [],
        "sources": [],
        "errors": [],
        "round": 0,
        "max_rounds": int(max_rounds or settings.research_max_rounds),
        "pending_queries": list(seed_queries) if seed_queries else [query],
        "pending_urls": [],
        "search_exhausted": False,
    }
    final_state: dict[str, Any] = await graph.ainvoke(initial_state)
    # Deduplicate sources by URL, preserving first-seen order.
    unique_sources: dict[str, WebSource] = {}
    for source in final_state.get("sources") or []:
        unique_sources.setdefault(source.url, source)
    # Deduplicate errors while preserving order.
    seen_errors: set[str] = set()
    errors: list[str] = []
    for err in final_state.get("errors") or []:
        if err not in seen_errors:
            seen_errors.add(err)
            errors.append(err)
    return {
        "verified_claims": list(final_state.get("claims") or []),
        "sources": list(unique_sources.values()),
        "errors": errors,
        "search_exhausted": bool(final_state.get("search_exhausted")),
        "rounds": int(final_state.get("round") or 0),
    }


class FactCheckerExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = initial_task_or_new(context)
        await event_queue.enqueue_event(task)

        payload = _extract_payload(context)
        query = str(payload.get("query") or "")
        claims = _coerce_claims(payload.get("claims") or [])
        seed_queries = _coerce_str_list(payload.get("seed_queries") or [])

        try:
            result: FactCheckRunResult = await run_fact_check(query, claims, seed_queries)
            error_text: str | None = None
            exhausted = bool(result["search_exhausted"])
            errors_list = list(result["errors"])
            if exhausted and not result["sources"]:
                status = TaskState.failed
                error_text = "FactChecker could not gather web evidence — " + (
                    " | ".join(errors_list)
                    if errors_list
                    else "no hits and no provider-level errors reported."
                )
            else:
                status = TaskState.completed
        except Exception as exc:
            logger.exception("FactChecker crashed task_id=%s", task.id)
            result = {
                "verified_claims": claims,
                "sources": [],
                "errors": [f"FactChecker crashed: {exc}"],
                "search_exhausted": True,
                "rounds": 0,
            }
            status = TaskState.failed
            error_text = str(exc)

        artifact = Artifact(
            artifact_id="verified",
            name="verified",
            parts=[
                Part(
                    root=DataPart(
                        data={
                            "verified_claims": [
                                c.model_dump(mode="json") for c in result["verified_claims"]
                            ],
                            "sources": [s.model_dump(mode="json") for s in result["sources"]],
                            "errors": list(result["errors"]),
                            "search_exhausted": bool(result["search_exhausted"]),
                            "rounds": result["rounds"],
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


def _coerce_claims(raw: Any) -> list[Claim]:
    claims: list[Claim] = []
    for item in raw or []:
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if isinstance(item, dict):
            try:
                claims.append(Claim.model_validate(item))
            except ValidationError:
                continue
    return claims


def _coerce_str_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []
