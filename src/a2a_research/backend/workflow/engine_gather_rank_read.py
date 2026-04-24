"""Rank and read helpers for evidence gathering."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.coerce import coerce_page_content
from a2a_research.backend.workflow.status import emit_envelope, emit_step

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        Claim,
        ClaimState,
        ResearchSession,
        WorkflowBudget,
    )
    from a2a_research.backend.tools import PageContent, WebHit

logger = get_logger(__name__)


async def run_rank_stage(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    claim_state: ClaimState,
    to_process: list[Claim],
    hits: list[WebHit],
    update_wall_seconds: Callable[[], None],
    loop_round: int,
    back_channel: dict[str, Any] | None = None,
) -> tuple[list[str], dict[str, Any]] | None:
    rank_result = await _run_agent(
        session,
        client,
        AgentRole.RANKER,
        {
            "hits": [h.model_dump(mode="json") for h in hits],
            "unresolved_claims": [
                c.model_dump(mode="json") for c in to_process
            ],
            "freshness_windows": {
                key: value.model_dump(mode="json")
                for key, value in claim_state.freshness_windows.items()
            },
            "session_id": session.id,
            "trace_id": session.trace_id,
            **{
                k: v
                for k, v in (back_channel or {}).items()
                if k not in {"session_id", "trace_id"}
            },
        },
    )
    ranked_urls = [str(url) for url in (rank_result.get("ranked_urls") or [])]
    fetch_budget = max(
        0,
        min(budget.max_urls_fetched - session.budget_consumed.urls_fetched, 8),
    )
    urls_to_fetch = ranked_urls[:fetch_budget]
    update_wall_seconds()
    if urls_to_fetch:
        return urls_to_fetch, rank_result
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=AgentRole.RANKER,
            code=ErrorCode.ALL_URLS_FILTERED,
            severity=ErrorSeverity.DEGRADED,
            retryable=True,
            root_cause=f"All URLs filtered by ranker in round {loop_round}.",
            trace_id=session.trace_id,
        ),
        session,
    )
    return None


async def run_read_stage(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    to_process: list[Claim],
    urls_to_fetch: list[str],
    rank_result: dict[str, Any],
    update_wall_seconds: Callable[[], None],
    emit_budget: Callable[[str, AgentRole, str], None],
    loop_round: int,
) -> tuple[list[PageContent], dict[str, Any]] | None:
    emit_step(
        session.id,
        AgentRole.READER,
        ProgressPhase.STEP_STARTED,
        "reading_urls",
    )
    read_result = await _run_agent(
        session,
        client,
        AgentRole.READER,
        {
            "urls": urls_to_fetch,
            "claims": [c.model_dump(mode="json") for c in to_process],
            "session_id": session.id,
            "trace_id": session.trace_id,
            "backup_urls": rank_result.get("backup_urls", []),
            "revised_order": rank_result.get("revised_order", []),
            "fetch_priority": rank_result.get("fetch_priority", []),
        },
    )
    pages = [
        page
        for page in (
            coerce_page_content(raw) for raw in read_result.get("pages", [])
        )
        if page is not None and not page.error and page.markdown
    ]
    session.budget_consumed.urls_fetched += len(urls_to_fetch)
    update_wall_seconds()
    if not pages:
        emit_envelope(
            session.id,
            ErrorEnvelope(
                role=AgentRole.READER,
                code=ErrorCode.UNREADABLE_PAGES,
                severity=ErrorSeverity.DEGRADED,
                retryable=True,
                root_cause=(
                    f"No readable pages extracted in round {loop_round}."
                ),
                partial_results={
                    "attempted_urls": urls_to_fetch,
                    "parser_failures": read_result.get("unreadable_urls", []),
                },
                trace_id=session.trace_id,
            ),
            session,
        )
        return None
    if not session.budget_consumed.is_exhausted(budget):
        return pages, read_result
    logger.info("Budget exhausted after read in round %s", loop_round)
    emit_budget(session.id, AgentRole.READER, "budget_exhausted_after_read")
    return None
