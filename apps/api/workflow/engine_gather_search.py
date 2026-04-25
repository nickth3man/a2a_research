"""Search-stage helpers for evidence gathering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from core import AgentRole, WebSource, get_logger
from core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from workflow import coerce_web_hit, emit_envelope
from workflow import run_agent as _run_agent

if TYPE_CHECKING:
    from collections.abc import Callable

    from core import A2AClient
    from core.models import (
        ClaimState,
        ResearchSession,
        WorkflowBudget,
    )
    from tools import WebHit

logger = get_logger(__name__)


async def run_search_stage(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    claim_state: ClaimState,
    claim_queries: list[str],
    update_wall_seconds: Callable[[], None],
    emit_budget: Callable[[str, AgentRole, str], None],
    loop_round: int,
) -> tuple[list[WebHit], dict[str, Any]] | None:
    search_result = await _run_agent(
        session,
        client,
        AgentRole.SEARCHER,
        {
            "queries": claim_queries,
            "freshness_hints": {
                key: value.model_dump(mode="json")
                for key, value in claim_state.freshness_windows.items()
            },
            "session_id": session.id,
            "trace_id": session.trace_id,
        },
    )
    hits = [
        hit
        for hit in (
            coerce_web_hit(raw) for raw in search_result.get("hits", [])
        )
        if hit is not None
    ]
    update_sources(session, hits)
    update_wall_seconds()
    if not hits:
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.SEARCHER,
                code=ErrorCode.NO_HITS,
                severity=ErrorSeverity.DEGRADED,
                retryable=True,
                root_cause=f"Search returned no hits in round {loop_round}.",
                partial_results={
                    "attempted_queries": claim_queries,
                    "round": loop_round,
                },
                trace_id=session.trace_id,
            ),
            session,
        )
        return None
    if not session.budget_consumed.is_exhausted(budget):
        back_channel = {k: v for k, v in search_result.items() if k != "hits"}
        return hits, back_channel
    logger.info("Budget exhausted after search in round %s", loop_round)
    emit_budget(
        session.id, AgentRole.SEARCHER, "budget_exhausted_after_search"
    )
    return None


def update_sources(session: ResearchSession, hits: list[WebHit]) -> None:
    existing_urls = {source.url for source in session.sources}
    for hit in hits:
        if hit.url in existing_urls:
            continue
        session.sources.append(
            WebSource(url=hit.url, title=hit.title, excerpt=hit.snippet)
        )
        existing_urls.add(hit.url)
