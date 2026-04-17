"""Verify node and router for the FactChecker LangGraph loop."""

from __future__ import annotations

from typing import Any, Literal

from a2a_research.agents.langgraph.fact_checker.node_support import (
    build_verify_prompt,
    parse_verifier,
)
from a2a_research.agents.langgraph.fact_checker.prompt import VERIFY_PROMPT
from a2a_research.agents.langgraph.fact_checker.state import FactCheckState  # noqa: TC001
from a2a_research.app_logging import get_logger
from a2a_research.models import Verdict
from a2a_research.providers import ProviderRequestError, get_llm

logger = get_logger(__name__)

__all__ = ["build_verify_node", "route"]


def build_verify_node() -> Any:
    async def verify(state: FactCheckState) -> dict[str, Any]:
        claims = list(state.get("claims") or [])
        evidence = list(state.get("evidence") or [])
        errors = list(state.get("errors") or [])
        next_round = int(state.get("round") or 0) + 1

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
            return {
                "claims": degraded,
                "round": next_round,
                "pending_queries": [],
                "search_exhausted": True,
            }

        user_content = build_verify_prompt(state.get("query", ""), claims, evidence)
        try:
            model = get_llm()
            response = model.invoke(
                [
                    {"role": "system", "content": VERIFY_PROMPT},
                    {"role": "user", "content": user_content},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("FactChecker LLM failed: %s", exc)
            raw = ""
        new_claims, follow_ups = parse_verifier(raw, fallback=claims)
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
