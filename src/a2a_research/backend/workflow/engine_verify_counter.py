"""Counter-evidence helpers for adversary stage."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from a2a_research.backend.core.models import AgentRole
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.status import emit_envelope

if TYPE_CHECKING:
    from collections.abc import Callable

    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        ResearchSession,
        WorkflowBudget,
    )


async def collect_counter_evidence(
    session: ResearchSession,
    client: A2AClient,
    budget: WorkflowBudget,
    counter_queries: list[Any],
    adv_payload: dict[str, Any],
    update_wall_seconds: Callable[[], None],
) -> bool:
    if not counter_queries:
        return True
    adv_sea_result = await _run_agent(
        session,
        client,
        AgentRole.SEARCHER,
        {
            "queries": counter_queries,
            "session_id": session.id,
            "trace_id": session.trace_id,
            "mode": "counter_evidence",
        },
    )
    counter_hits: list[dict[str, Any]] = []
    for hit in adv_sea_result.get("hits", []):
        if isinstance(hit, dict):
            counter_hits.append(cast(dict[str, Any], hit))
    adv_payload["counter_hits"] = counter_hits
    update_wall_seconds()
    if session.budget_consumed.is_exhausted(budget):
        emit_budget_exhausted(
            session,
            AgentRole.SEARCHER,
            "Budget exhausted: adversarial search.",
        )
        return False
    counter_urls = [
        str(hit.get("url", "")) for hit in counter_hits if hit.get("url")
    ][:4]
    if not counter_urls:
        return True
    adv_rea_result = await _run_agent(
        session,
        client,
        AgentRole.READER,
        {
            "urls": counter_urls,
            "session_id": session.id,
            "trace_id": session.trace_id,
            "mode": "counter_evidence",
        },
    )
    adv_payload["counter_pages"] = adv_rea_result.get("pages", [])
    update_wall_seconds()
    if not session.budget_consumed.is_exhausted(budget):
        return True
    emit_budget_exhausted(
        session,
        AgentRole.READER,
        "Budget exhausted: adversarial reading.",
    )
    return False


def emit_budget_exhausted(
    session: ResearchSession,
    role: AgentRole,
    root_cause: str,
) -> None:
    emit_envelope(
        session.id,
        ErrorEnvelope(
            role=role,
            code=ErrorCode.BUDGET_EXHAUSTED_AFTER_VERIFY,
            severity=ErrorSeverity.DEGRADED,
            retryable=False,
            root_cause=root_cause,
            trace_id=session.trace_id,
        ),
        session,
    )
