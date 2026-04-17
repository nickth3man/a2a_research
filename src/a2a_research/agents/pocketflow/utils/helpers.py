"""Deterministic helpers for parsing LLM output and building markdown reports.

JSON/text extraction for claims and verdicts, formatting helpers, and a small
PocketFlow ``Flow`` used to assemble report sections without an LLM when needed.
"""

from __future__ import annotations

from typing import Any, cast

from pocketflow import Flow, Node

from a2a_research.json_utils import parse_json_safely as parse_json_safely
from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ResearchSession,
    Verdict,
)


def normalize_claim_id(raw_id: Any, fallback: str) -> str:
    if raw_id is None:
        return fallback

    normalized = str(raw_id).strip()
    return normalized or fallback


class _ReportHeaderNode(Node):
    def prep(self, shared: dict[str, Any]) -> Any:
        return shared["session"]

    def exec(self, prep_res: Any) -> Any:
        session = cast("ResearchSession", prep_res)
        return f"# Research Report\n**Query:** {session.query}\n\n---\n\n## Verified Claims\n\n"

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: Any) -> Any:
        shared["parts"].append(exec_res)
        return "default"


class _ClaimsSectionNode(Node):
    def prep(self, shared: dict[str, Any]) -> Any:
        session: ResearchSession = shared["session"]
        return session.get_agent(AgentRole.VERIFIER).claims

    def exec(self, prep_res: Any) -> Any:
        claims = cast("list[Claim]", prep_res)
        return format_claims_section(claims)

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: Any) -> Any:
        shared["parts"].append(exec_res)
        shared["claims"] = prep_res
        return "default"


class _SummaryNode(Node):
    def prep(self, shared: dict[str, Any]) -> Any:
        return list(shared.get("claims", []))

    def exec(self, prep_res: Any) -> Any:
        claims = cast("list[Claim]", prep_res)
        supported = sum(1 for c in claims if c.verdict == Verdict.SUPPORTED)
        refuted = sum(1 for c in claims if c.verdict == Verdict.REFUTED)
        inconclusive = len(claims) - supported - refuted
        return (
            "\n---\n"
            "## Summary\n\n"
            f"- **{supported}** claims supported  \n"
            f"- **{refuted}** claims refuted  \n"
            f"- **{inconclusive}** inconclusive\n"
        )

    def post(self, shared: dict[str, Any], prep_res: Any, exec_res: Any) -> Any:
        shared["parts"].append(exec_res)
        return "default"


def create_result(
    role: AgentRole,
    status: AgentStatus,
    message: str,
    **kwargs: Any,
) -> AgentResult:
    return AgentResult(role=role, status=status, message=message, **kwargs)


def format_claim_verdict(verdict: Verdict) -> str:
    if verdict == Verdict.SUPPORTED:
        return "✅ SUPPORTED"
    if verdict == Verdict.REFUTED:
        return "❌ REFUTED"
    return "⚠️  INSUFFICIENT_EVIDENCE"


def format_confidence(confidence: float) -> str:
    return f"{confidence:.0%}"


def format_claims_section(claims: list[Claim]) -> str:
    if not claims:
        return "No claims to display."
    lines: list[str] = []
    for i, claim in enumerate(claims, 1):
        badge = format_claim_verdict(claim.verdict)
        conf = format_confidence(claim.confidence)
        lines.append(f"{i}. **{claim.text}**  \n{badge} · confidence {conf}")
        if claim.evidence_snippets:
            for snippet in claim.evidence_snippets:
                lines.append(f"   > {snippet}")
        if claim.sources:
            lines.append(f"   Sources: {', '.join(claim.sources)}")
        lines.append("")
    return "\n".join(lines)


def build_markdown_report(session: ResearchSession) -> str:
    shared: dict[str, Any] = {"session": session, "parts": [], "claims": []}
    header = _ReportHeaderNode()
    claims_node = _ClaimsSectionNode()
    summary = _SummaryNode()
    _ = header >> claims_node >> summary
    Flow(start=header).run(shared)
    return "".join(shared["parts"])



def extract_claims_from_llm_output(raw: str) -> list[Claim]:
    data = parse_json_safely(raw)
    if not data:
        return []
    claims_list = data.get("verified_claims") or data.get("atomic_claims") or []
    results: list[Claim] = []
    for item in claims_list:
        if isinstance(item, dict):
            text = item.get("text", item.get("claim", ""))
            if not text:
                continue
            verdict_str = item.get("verdict", "INSUFFICIENT_EVIDENCE")
            try:
                verdict = Verdict(verdict_str)
            except ValueError:
                verdict = Verdict.INSUFFICIENT_EVIDENCE
            claim = Claim(
                id=normalize_claim_id(item.get("id"), f"clm_{len(results)}"),
                text=text,
                confidence=float(item.get("confidence", 0.5)),
                verdict=verdict,
                sources=item.get("sources", []),
                evidence_snippets=item.get("evidence_snippets", []),
            )
            results.append(claim)
    return results


def extract_research_summary(raw: str) -> str:
    data = parse_json_safely(raw)
    return data.get("research_summary", raw[:500]) if isinstance(data, dict) else raw[:500]


def extract_report_markdown(raw: str) -> str:
    data = parse_json_safely(raw)
    if isinstance(data, dict):
        report = data.get("report")
        if isinstance(report, str) and report.strip():
            return report.strip()
    return raw.strip()


def aggregate_citations(agent_results: dict[AgentRole, AgentResult]) -> list[str]:
    citations: set[str] = set()
    for result in agent_results.values():
        for cite in result.citations:
            citations.add(cite)
    return sorted(citations)
