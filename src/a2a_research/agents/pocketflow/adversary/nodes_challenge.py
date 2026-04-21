"""PocketFlow nodes for the Adversary agent - Challenge node."""

from __future__ import annotations

from typing import Any, Literal

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.adversary.prompt import CHALLENGE_PROMPT
from a2a_research.logging.app_logging import get_logger
from a2a_research.utils.json_utils import parse_json_safely
from a2a_research.models import (
    AgentRole,
    Claim,
    ClaimVerification,
    IndependenceGraph,
)
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.llm.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings
from a2a_research.utils.timing import perf_counter
from a2a_research.utils.validation import to_float

logger = get_logger(__name__)

ChallengeResult = Literal["HOLDS", "WEAKENED", "REFUTED"]


def _fallback_challenge(
    evaluation: dict[str, Any], independence_count: int
) -> dict[str, Any]:
    quality = evaluation.get("quality_score", 0.5)
    independence = evaluation.get("independence_score", 0.5)
    contradictions = evaluation.get("contradictions_found", [])
    weak_ids = evaluation.get("weak_evidence_ids", [])

    if contradictions or (quality < 0.3 and independence < 0.3):
        result: ChallengeResult = "REFUTED"
    elif (
        weak_ids
        or quality < 0.5
        or independence < 0.5
        or independence_count < 2
    ):
        result = "WEAKENED"
    else:
        result = "HOLDS"

    return {
        "challenge_result": result,
        "reasoning": (
            f"Fallback challenge: quality={quality}, "
            f"independence={independence}, sources={independence_count}"
        ),
        "confidence_adjustment": (
            -0.2
            if result == "REFUTED"
            else (-0.1 if result == "WEAKENED" else 0.0)
        ),
    }


def _parse_challenge(
    data: dict[str, Any] | None,
    evaluation: dict[str, Any],
    independence_count: int,
) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _fallback_challenge(evaluation, independence_count)

    raw_result = str(data.get("challenge_result") or "").upper()
    if raw_result not in {"HOLDS", "WEAKENED", "REFUTED"}:
        return _fallback_challenge(evaluation, independence_count)

    result: ChallengeResult = raw_result  # type: ignore[assignment]

    return {
        "challenge_result": result,
        "reasoning": str(data.get("reasoning") or ""),
        "confidence_adjustment": to_float(
            data.get("confidence_adjustment"), 0.0
        ),
    }


class ChallengeNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        claim = shared.get("claim")
        if not isinstance(claim, Claim):
            raise ValueError("Adversary shared store missing Claim.")
        return {
            "claim": claim,
            "tentative_verdict": shared.get("tentative_verdict"),
            "evaluation": shared.get("evaluation"),
            "independence_graph": shared.get("independence_graph"),
        }

    async def exec_async(self, prep_res: dict[str, Any]) -> dict[str, Any]:
        claim: Claim = prep_res["claim"]
        evaluation: dict[str, Any] = prep_res.get("evaluation") or {}
        graph: IndependenceGraph | None = prep_res.get("independence_graph")
        verdict = prep_res.get("tentative_verdict")

        independence_count = (
            graph.independent_source_count(claim.id)
            if graph is not None
            else getattr(verdict, "independent_source_count", 0)
        )

        prompt = (
            f"Claim: {claim.text}\n"
            f"Tentative verdict: {getattr(verdict, 'verdict', 'UNKNOWN')}\n"
            f"Independent sources: {independence_count}\n\n"
            f"Evidence evaluation:\n"
            f"- Gaps: {evaluation.get('evidence_gaps', [])}\n"
            f"- Bias: {evaluation.get('bias_assessment', 'unknown')}\n"
            f"- Independence score: "
            f"{evaluation.get('independence_score', 0.0)}\n"
            f"- Quality score: {evaluation.get('quality_score', 0.0)}\n"
            f"- Contradictions: {evaluation.get('contradictions_found', [])}\n"
            f"- Weak evidence IDs: {evaluation.get('weak_evidence_ids', [])}\n"
            f"- Reasoning: {evaluation.get('evaluation_reasoning', '')}"
        )

        emit_prompt(
            AgentRole.ADVERSARY,
            "challenge",
            prompt,
            system_text=CHALLENGE_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": CHALLENGE_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning("Adversary LLM failed in challenge: %s", exc)
            return _fallback_challenge(evaluation, independence_count)

        emit_llm_response(
            AgentRole.ADVERSARY,
            "challenge",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        return _parse_challenge(data, evaluation, independence_count)

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: dict[str, Any],
    ) -> str:
        shared["challenge_result"] = exec_res.get("challenge_result", "HOLDS")
        shared["challenge_reasoning"] = exec_res.get("reasoning", "")
        shared["confidence_adjustment"] = exec_res.get(
            "confidence_adjustment", 0.0
        )
        return "default"


__all__ = ["ChallengeNode", "ChallengeResult"]
