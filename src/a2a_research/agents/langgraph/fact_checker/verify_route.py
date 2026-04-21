"""Verify logic for the FactChecker role.

Exposes :func:`verify_claims` for direct use by the coordinator.
"""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from a2a_research.agents.langgraph.fact_checker.node_support import (
    build_verify_prompt,
    parse_verifier,
)
from a2a_research.agents.langgraph.fact_checker.prompt import VERIFY_PROMPT
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole, Claim, Verdict
from a2a_research.progress import (
    ProgressPhase,
    emit,
    emit_claim_verdict,
    emit_llm_response,
    emit_prompt,
)
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

if TYPE_CHECKING:
    from a2a_research.tools import PageContent

logger = get_logger(__name__)

__all__ = ["verify_claims"]


async def verify_claims(
    query: str,
    claims: list[Claim],
    evidence: list[PageContent],
    *,
    session_id: str = "",
) -> list[Claim]:
    """Verify claims against evidence and return updated claims."""
    emit(
        session_id,
        ProgressPhase.STEP_SUBSTEP,
        AgentRole.FACT_CHECKER,
        3,
        5,
        "verify",
        detail=f"claims={len(claims)} evidence={len(evidence)}",
    )

    if not evidence:
        reason = "No web evidence was provided for verification."
        logger.warning("FactChecker verify short-circuit reason=%s", reason)
        return [
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

    user_content = build_verify_prompt(query, claims, evidence)
    emit_prompt(
        AgentRole.FACT_CHECKER,
        "verify",
        user_content,
        system_text=VERIFY_PROMPT,
        model=settings.llm.model,
        session_id=session_id,
    )
    started = perf_counter()
    response = None
    try:
        model = get_llm()
        response = await model.ainvoke(
            [
                {"role": "system", "content": VERIFY_PROMPT},
                {"role": "user", "content": user_content},
            ]
        )
        raw = getattr(response, "content", None) or str(response)
    except ProviderRequestError as exc:
        logger.warning("FactChecker LLM failed: %s", exc)
        raw = ""
    emit_llm_response(
        AgentRole.FACT_CHECKER,
        "verify",
        raw,
        elapsed_ms=(perf_counter() - started) * 1000,
        model=settings.llm.model,
        session_id=session_id,
        prompt_tokens=getattr(response, "prompt_tokens", None),
        completion_tokens=getattr(response, "completion_tokens", None),
        finish_reason=getattr(response, "finish_reason", ""),
    )
    new_claims, _follow_ups = parse_verifier(raw, fallback=claims)
    old_by_id = {c.id: c for c in claims}
    for claim in new_claims:
        prior = old_by_id.get(claim.id)
        old_verdict = prior.verdict.value if prior else "∅"
        new_verdict = claim.verdict.value
        if (
            not prior
            or old_verdict != new_verdict
            or (prior and prior.confidence != claim.confidence)
        ):
            emit_claim_verdict(
                AgentRole.FACT_CHECKER,
                claim.id,
                claim.text,
                old_verdict,
                new_verdict,
                confidence=claim.confidence,
                source_count=len(claim.sources or []),
                session_id=session_id,
            )
    logger.info(
        "FactChecker verify claims=%s",
        len(new_claims),
    )
    return new_claims
