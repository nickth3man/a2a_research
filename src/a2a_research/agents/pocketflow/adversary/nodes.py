"""PocketFlow nodes for the Adversary agent."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.adversary.prompt import (
    CHALLENGE_PROMPT,
    EVALUATE_EVIDENCE_PROMPT,
    INVERSION_QUERY_PROMPT,
)
from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import (
    AgentRole,
    Claim,
    ClaimVerification,
    EvidenceUnit,
    IndependenceGraph,
)
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.providers import ProviderRequestError, get_llm
from a2a_research.settings import settings

logger = get_logger(__name__)

ChallengeResult = Literal["HOLDS", "WEAKENED", "REFUTED"]

__all__ = [
    "ChallengeNode",
    "EvaluateEvidenceNode",
    "GenerateInversionQueriesNode",
    "TerminalNode",
]


class TerminalNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> None:
        return None

    async def exec_async(self, prep_res: None) -> None:
        return None

    async def post_async(
        self, shared: dict[str, Any], prep_res: None, exec_res: None
    ) -> str:
        return "done"


class GenerateInversionQueriesNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        claim = shared.get("claim")
        if not isinstance(claim, Claim):
            raise ValueError("Adversary shared store missing Claim.")
        return {
            "claim": claim,
            "tentative_verdict": shared.get("tentative_verdict"),
        }

    async def exec_async(self, prep_res: dict[str, Any]) -> dict[str, Any]:
        claim: Claim = prep_res["claim"]
        verdict = prep_res.get("tentative_verdict")
        verdict_str = (
            verdict.verdict.value
            if isinstance(verdict, ClaimVerification)
            else "UNKNOWN"
        )

        prompt = (
            f"Claim: {claim.text}\n"
            f"Tentative verdict: {verdict_str}\n"
            f"Confidence: {getattr(verdict, 'confidence', 0.0)}"
        )

        emit_prompt(
            AgentRole.ADVERSARY,
            "inversion_queries",
            prompt,
            system_text=INVERSION_QUERY_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": INVERSION_QUERY_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning(
                "Adversary LLM failed in inversion queries: %s", exc
            )
            return {"inversion_queries": [], "error": str(exc)}

        emit_llm_response(
            AgentRole.ADVERSARY,
            "inversion_queries",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        queries = []
        if isinstance(data, dict):
            raw_queries = data.get("inversion_queries") or []
            if isinstance(raw_queries, list):
                queries = [
                    str(q).strip()
                    for q in raw_queries
                    if isinstance(q, str) and str(q).strip()
                ]

        if not queries:
            queries = _fallback_inversion_queries(claim.text)

        return {"inversion_queries": queries, "error": None}

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: dict[str, Any],
    ) -> str:
        shared["inversion_queries"] = exec_res["inversion_queries"]
        shared["error"] = exec_res.get("error")
        return "default"


class EvaluateEvidenceNode(AsyncNode):
    async def prep_async(self, shared: dict[str, Any]) -> dict[str, Any]:
        claim = shared.get("claim")
        if not isinstance(claim, Claim):
            raise ValueError("Adversary shared store missing Claim.")
        return {
            "claim": claim,
            "tentative_verdict": shared.get("tentative_verdict"),
            "evidence": list(shared.get("evidence") or []),
            "independence_graph": shared.get("independence_graph"),
        }

    async def exec_async(self, prep_res: dict[str, Any]) -> dict[str, Any]:
        claim: Claim = prep_res["claim"]
        evidence: list[EvidenceUnit] = prep_res["evidence"]
        graph: IndependenceGraph | None = prep_res.get("independence_graph")
        verdict = prep_res.get("tentative_verdict")

        evidence_summary = _summarize_evidence(evidence, graph, claim.id)
        verdict_str = (
            verdict.verdict.value
            if isinstance(verdict, ClaimVerification)
            else "UNKNOWN"
        )

        prompt = (
            f"Claim: {claim.text}\n"
            f"Tentative verdict: {verdict_str}\n"
            f"Independent source count: {getattr(verdict, 'independent_source_count', 0)}\n\n"
            f"Evidence summary:\n{evidence_summary}"
        )

        emit_prompt(
            AgentRole.ADVERSARY,
            "evaluate_evidence",
            prompt,
            system_text=EVALUATE_EVIDENCE_PROMPT,
            model=settings.llm.model,
        )
        started = perf_counter()
        try:
            model = get_llm()
            response = await model.ainvoke(
                [
                    {"role": "system", "content": EVALUATE_EVIDENCE_PROMPT},
                    {"role": "user", "content": prompt},
                ]
            )
            raw = getattr(response, "content", None) or str(response)
        except ProviderRequestError as exc:
            logger.warning(
                "Adversary LLM failed in evidence evaluation: %s", exc
            )
            return _fallback_evaluation(evidence)

        emit_llm_response(
            AgentRole.ADVERSARY,
            "evaluate_evidence",
            raw,
            elapsed_ms=(perf_counter() - started) * 1000,
            model=settings.llm.model,
            prompt_tokens=getattr(response, "prompt_tokens", None),
            completion_tokens=getattr(response, "completion_tokens", None),
            finish_reason=getattr(response, "finish_reason", ""),
        )

        data = parse_json_safely(raw)
        return _parse_evaluation(data, evidence)

    async def post_async(
        self,
        shared: dict[str, Any],
        prep_res: dict[str, Any],
        exec_res: dict[str, Any],
    ) -> str:
        shared["evaluation"] = exec_res
        return "default"


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
            f"- Independence score: {evaluation.get('independence_score', 0.0)}\n"
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


def _fallback_inversion_queries(claim_text: str) -> list[str]:
    return [
        f"{claim_text} debunked",
        f"{claim_text} controversy",
        f"{claim_text} criticism",
    ]


def _summarize_evidence(
    evidence: list[EvidenceUnit],
    graph: IndependenceGraph | None,
    claim_id: str,
) -> str:
    lines: list[str] = []
    for ev in evidence:
        publisher = ev.publisher_id or ev.domain_authority or "unknown"
        cluster = ev.syndication_cluster_id or "none"
        lines.append(
            f"- [{ev.id}] {ev.title or ev.url} "
            f"(publisher={publisher}, type={ev.source_type}, cluster={cluster})"
        )
    if graph is not None:
        lines.append(
            f"\nIndependent source count for claim: {graph.independent_source_count(claim_id)}"
        )
        publishers = graph.claim_to_publishers.get(claim_id, set())
        if publishers:
            lines.append(f"Publishers: {', '.join(sorted(publishers))}")
    return "\n".join(lines) if lines else "No evidence provided."


def _fallback_evaluation(evidence: list[EvidenceUnit]) -> dict[str, Any]:
    return {
        "evidence_gaps": [],
        "bias_assessment": "unknown",
        "independence_score": 0.5,
        "quality_score": 0.5,
        "contradictions_found": [],
        "weak_evidence_ids": [],
        "evaluation_reasoning": "LLM evaluation failed; using neutral fallback.",
    }


def _parse_evaluation(
    data: dict[str, Any] | None, evidence: list[EvidenceUnit]
) -> dict[str, Any]:
    if not isinstance(data, dict):
        return _fallback_evaluation(evidence)

    bias = str(data.get("bias_assessment") or "unknown").lower()
    if bias not in {"one-sided", "balanced", "mixed", "unknown"}:
        bias = "unknown"

    return {
        "evidence_gaps": _to_str_list(data.get("evidence_gaps")),
        "bias_assessment": bias,
        "independence_score": _to_float(data.get("independence_score"), 0.5),
        "quality_score": _to_float(data.get("quality_score"), 0.5),
        "contradictions_found": _to_str_list(data.get("contradictions_found")),
        "weak_evidence_ids": _to_str_list(data.get("weak_evidence_ids")),
        "evaluation_reasoning": str(data.get("evaluation_reasoning") or ""),
    }


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
        "reasoning": f"Fallback challenge: quality={quality}, independence={independence}, sources={independence_count}",
        "confidence_adjustment": -0.2
        if result == "REFUTED"
        else (-0.1 if result == "WEAKENED" else 0.0),
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
        "confidence_adjustment": _to_float(
            data.get("confidence_adjustment"), 0.0
        ),
    }


def _to_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


def _to_float(value: Any, default: float) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (ValueError, TypeError):
        return default
