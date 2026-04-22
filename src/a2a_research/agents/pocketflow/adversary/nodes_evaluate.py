"""PocketFlow nodes for the Adversary agent - Evidence Evaluation."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncNode

from a2a_research.agents.pocketflow.adversary.prompt import (
    EVALUATE_EVIDENCE_PROMPT,
)
from a2a_research.llm.providers import ProviderRequestError, get_llm
from a2a_research.logging.app_logging import get_logger
from a2a_research.models import (
    AgentRole,
    Claim,
    ClaimVerification,
    EvidenceUnit,
    IndependenceGraph,
)
from a2a_research.progress import emit_llm_response, emit_prompt
from a2a_research.settings import settings
from a2a_research.utils.json_utils import parse_json_safely
from a2a_research.utils.timing import perf_counter
from a2a_research.utils.validation import to_float, to_str_list

logger = get_logger(__name__)


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
            f"(publisher={publisher}, type={ev.source_type}, "
            f"cluster={cluster})"
        )
    if graph is not None:
        lines.append(
            f"\nIndependent source count for claim: "
            f"{graph.independent_source_count(claim_id)}"
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
        "evaluation_reasoning": (
            "LLM evaluation failed; using neutral fallback."
        ),
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
        "evidence_gaps": to_str_list(data.get("evidence_gaps")),
        "bias_assessment": bias,
        "independence_score": to_float(data.get("independence_score"), 0.5),
        "quality_score": to_float(data.get("quality_score"), 0.5),
        "contradictions_found": to_str_list(data.get("contradictions_found")),
        "weak_evidence_ids": to_str_list(data.get("weak_evidence_ids")),
        "evaluation_reasoning": str(data.get("evaluation_reasoning") or ""),
    }


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
            f"Independent source count: "
            f"{getattr(verdict, 'independent_source_count', 0)}\n\n"
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


__all__ = ["EvaluateEvidenceNode"]
