"""Fact checker core logic."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.agents.langgraph.fact_checker.verify_route import (
    verify_claims,
)
from a2a_research.logging.app_logging import get_logger
from a2a_research.models import AgentRole, Claim, Verdict, WebSource
from a2a_research.progress import ProgressPhase, emit

if TYPE_CHECKING:
    from a2a_research.agents.langgraph.fact_checker.state import (
        FactCheckRunResult,
    )
    from a2a_research.tools import PageContent

logger = get_logger(__name__)


async def run_fact_check(
    query: str,
    claims: list[Claim],
    evidence: list[PageContent],
    sources: list[WebSource],
    *,
    session_id: str = "",
) -> FactCheckRunResult:
    """Verify claims against provided evidence; return
    ``{verified_claims, sources}``.
    """
    if not evidence:
        reason = "No web evidence was provided for verification."
        logger.warning("FactChecker verify short-circuit reason=%s", reason)
        degraded = [
            c.model_copy(
                update={
                    "verdict": Verdict.INSUFFICIENT_EVIDENCE,
                    "confidence": 0.0,
                    "sources": [],
                    "evidence_snippets": [reason],
                }
            )
            for c in claims
        ]
        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.FACT_CHECKER,
            3,
            5,
            "exhausted",
            detail=reason,
        )
        return {
            "verified_claims": degraded,
            "sources": sources,
            "errors": [reason],
            "search_exhausted": True,
            "rounds": 0,
        }

    verified = await verify_claims(
        query, claims, evidence, session_id=session_id
    )
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.FACT_CHECKER,
        3,
        5,
        "completed",
        detail=f"claims={len(verified)}",
    )
    return {
        "verified_claims": verified,
        "sources": sources,
        "errors": [],
        "search_exhausted": False,
        "rounds": 1,
    }
