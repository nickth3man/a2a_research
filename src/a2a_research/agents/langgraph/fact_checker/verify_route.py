"""Verify node and router for the FactChecker LangGraph loop."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from a2a_research.agents.langgraph.fact_checker.node_support import (
    build_verify_prompt,
    parse_verifier,
)
from a2a_research.agents.langgraph.fact_checker.prompt import VERIFY_PROMPT
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState  # noqa: TC001
from a2a_research.app_logging import get_logger
from a2a_research.models import AgentRole, Verdict
from a2a_research.progress import (
    ProgressPhase,
    emit,
    emit_claim_verdict,
    emit_llm_response,
    emit_prompt,
)
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

logger = get_logger(__name__)

__all__ = ["build_verify_node", "route"]


def build_verify_node() -> Any:
    async def verify(state: FactCheckState) -> dict[str, Any]:
        claims = list(state.get("claims") or [])
        evidence = list(state.get("evidence") or [])
        errors = list(state.get("errors") or [])
        session_id = str(state.get("session_id") or "")
        next_round = int(state.get("round") or 0) + 1

        emit(
            session_id,
            ProgressPhase.STEP_SUBSTEP,
            AgentRole.FACT_CHECKER,
            3,
            5,
            f"round_{next_round}_verify",
            detail=f"claims={len(claims)} evidence={len(evidence)}",
        )

        if not evidence:
            reason = (
                "Web evidence was unavailable: " + " | ".join(errors)
                if errors
                else "No web evidence was retrieved and no provider-level errors were reported."
            )
            logger.warning(
                "FactChecker verify short-circuit round=%s reason=%s", next_round, reason
            )
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
                "claims": degraded,
                "round": next_round,
                "pending_queries": [],
                "search_exhausted": True,
            }

        user_content = build_verify_prompt(state.get("query", ""), claims, evidence)
        emit_prompt(
            AgentRole.FACT_CHECKER,
            f"verify_round_{next_round}",
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
            f"verify_round_{next_round}",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            session_id=session_id,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )
        new_claims, follow_ups = parse_verifier(raw, fallback=claims)
        old_by_id = {c.id: c for c in claims}
        for claim in new_claims:
            prior = old_by_id.get(claim.id)
            old_verdict = prior.verdict.value if prior else "∅"
            new_verdict = claim.verdict.value
            if not prior or old_verdict != new_verdict or (prior and prior.confidence != claim.confidence):
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
            "FactChecker verify round=%s claims=%s follow_ups=%s",
            next_round,
            len(new_claims),
            len(follow_ups),
        )
        return {
            "claims": new_claims,
            "round": next_round,
            "pending_queries": follow_ups,
        }

    return verify


def route(state: FactCheckState) -> Literal["continue", "done"]:
    max_rounds = int(state.get("max_rounds") or 3)
    current = int(state.get("round") or 0)
    if state.get("search_exhausted"):
        return "done"
    follow_ups = list(state.get("pending_queries") or [])
    if current >= max_rounds:
        return "done"
    if not follow_ups:
        return "done"
    claims = state.get("claims") or []
    if any(c.verdict == Verdict.NEEDS_MORE_EVIDENCE for c in claims):
        return "continue"
    return "done"
