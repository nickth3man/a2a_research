"""Agent implementations for the 4-agent research pipeline.

Each agent:
- Receives an AgentResult input from the previous agent (A2A-shaped, in-process)
- Calls the LLM with a system prompt and user context
- Returns an AgentResult for the next agent
"""

from __future__ import annotations

import json

from a2a_research.helpers import (
    aggregate_citations,
    build_markdown_report,
    extract_claims_from_llm_output,
    extract_report_markdown,
    extract_research_summary,
    parse_json_safely,
)
from a2a_research.models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ResearchSession,
    Verdict,
)
from a2a_research.prompts import (
    ANALYST_PROMPT,
    PRESENTER_PROMPT,
    RESEARCHER_PROMPT,
    VERIFIER_PROMPT,
)
from a2a_research.providers import get_llm
from a2a_research.rag import get_source_title, retrieve


def _call_llm(system_prompt: str, user_content: str) -> str:
    llm = get_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    response = llm.invoke(messages)
    return str(response.content) if hasattr(response, "content") else str(response)


def _invoke(
    role: AgentRole,
    status: AgentStatus,
    message: str,
    raw_content: str = "",
    claims: list[Claim] | None = None,
    citations: list[str] | None = None,
) -> AgentResult:
    return AgentResult(
        role=role,
        status=status,
        message=message,
        raw_content=raw_content,
        claims=claims or [],
        citations=citations or [],
    )


# ─── Researcher ────────────────────────────────────────────────────────────────


def researcher_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    query = str(message.payload.get("query", session.query) if message else session.query)
    try:
        chunks = retrieve(query, n_results=10)
    except Exception as exc:
        return _invoke(AgentRole.RESEARCHER, AgentStatus.FAILED, f"RAG retrieval failed: {exc}")

    max_sources = 10
    user_ctx = f"Research query: {query}\n\nRelevant corpus chunks (id, source, score, content):\n"
    for rc in chunks:
        user_ctx += (
            f"[{rc.chunk.id}] source={rc.chunk.source} "
            f"score={rc.score:.3f}\n{rc.chunk.content[:300]}\n\n"
        )

    user_ctx += "\nProduce your research summary based on the above chunks."
    raw = _call_llm(RESEARCHER_PROMPT.format(max_sources=max_sources), user_ctx)
    summary = extract_research_summary(raw)

    cited_sources = list({rc.chunk.source for rc in chunks})
    return _invoke(
        AgentRole.RESEARCHER,
        AgentStatus.COMPLETED,
        f"Retrieved {len(chunks)} chunks from {len(cited_sources)} sources.",
        raw_content=summary,
        citations=cited_sources,
    )


# ─── Analyst ──────────────────────────────────────────────────────────────────


def analyst_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    research_summary = (
        str(message.payload.get("research_summary", researcher_result.raw_content))
        if message
        else researcher_result.raw_content
    )
    user_ctx = (
        f"Research summary from Researcher:\n{research_summary}\n\n"
        f"Original query: {session.query}\n\n"
        "Decompose the query into atomic verifiable claims."
    )
    raw = _call_llm(ANALYST_PROMPT, user_ctx)
    claims = _parse_claims_from_analyst(raw)
    return _invoke(
        AgentRole.ANALYST,
        AgentStatus.COMPLETED,
        f"Decomposed into {len(claims)} atomic claims.",
        raw_content=raw,
        claims=claims,
    )


def _parse_claims_from_analyst(raw: str) -> list[Claim]:
    import re

    claims = extract_claims_from_llm_output(raw)
    if claims:
        return claims

    data = parse_json_safely(raw)

    if not data:
        text_blocks = re.findall(r'["\']([^"\']{20,})["\']', raw)
        for i, text in enumerate(text_blocks[:8]):
            text = text.strip()
            if text and len(text) > 15:
                claims.append(
                    Claim(id=f"clm_{i}", text=text, verdict=Verdict.INSUFFICIENT_EVIDENCE)
                )
        if not claims:
            for i, line in enumerate(raw.split("\n")):
                line = line.strip()
                if line and len(line) > 20 and not line.startswith("#"):
                    claims.append(
                        Claim(
                            id=f"clm_{i}", text=line[:200], verdict=Verdict.INSUFFICIENT_EVIDENCE
                        )
                    )
    else:
        for i, item in enumerate(data.get("atomic_claims", [])):
            if isinstance(item, dict):
                claims.append(
                    Claim(
                        id=item.get("id", f"clm_{i}"),
                        text=item.get("text", ""),
                        verdict=Verdict.INSUFFICIENT_EVIDENCE,
                    )
                )
    return claims


# ─── Verifier ────────────────────────────────────────────────────────────────


def verifier_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    analyst_result = session.get_agent(AgentRole.ANALYST)
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    if message and isinstance(message.payload.get("claims"), list):
        claims = [Claim.model_validate(item) for item in message.payload["claims"]]
    else:
        claims = analyst_result.claims
    query = str(message.payload.get("query", session.query) if message else session.query)

    try:
        chunks = retrieve(query, n_results=10)
    except Exception:
        chunks = []

    evidence_ctx = ""
    for rc in chunks:
        evidence_ctx += f"[{rc.chunk.source}] score={rc.score:.3f}\n{rc.chunk.content}\n\n"

    claims_ctx = "\n".join(f"- [{c.id}] {c.text}" for c in claims)

    user_ctx = (
        f"Claims to verify:\n{claims_ctx}\n\n"
        f"Evidence from corpus:\n{evidence_ctx}\n\n"
        "Assign verdicts and confidence scores to each claim."
    )
    raw = _call_llm(VERIFIER_PROMPT, user_ctx)

    verified = _parse_verified_claims(raw, claims)
    return _invoke(
        AgentRole.VERIFIER,
        AgentStatus.COMPLETED,
        f"Verified {len(verified)} claims.",
        raw_content=raw,
        claims=verified,
        citations=researcher_result.citations,
    )


def _parse_verified_claims(raw: str, fallback_claims: list[Claim]) -> list[Claim]:
    import re

    try:
        data = json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception:
        data = {}

    if data and "verified_claims" in data:
        verified: list[Claim] = []
        for item in data["verified_claims"]:
            if not isinstance(item, dict):
                continue
            text = item.get("text", "")
            verdict_str = item.get("verdict", "INSUFFICIENT_EVIDENCE")
            try:
                verdict = Verdict(verdict_str)
            except ValueError:
                verdict = Verdict.INSUFFICIENT_EVIDENCE
            evidence_snippets = item.get("evidence_snippets", [])
            if not evidence_snippets and isinstance(item.get("reasoning"), str):
                evidence_snippets = [item["reasoning"]]
            verified.append(
                Claim(
                    id=item.get("id", f"clm_{len(verified)}"),
                    text=text,
                    confidence=float(item.get("confidence", 0.5)),
                    verdict=verdict,
                    sources=item.get("sources", []),
                    evidence_snippets=evidence_snippets,
                )
            )
        return verified

    lines = raw.split("\n")
    results: list[Claim] = []
    current_text: list[str] = []
    current_verdict: Verdict | None = None
    current_confidence: float = 0.5
    current_sources: list[str] = []
    current_snippets: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_text and current_verdict:
                claim_text = " ".join(current_text)
                results.append(
                    Claim(
                        id=f"clm_{len(results)}",
                        text=claim_text,
                        confidence=current_confidence,
                        verdict=current_verdict,
                        sources=current_sources,
                        evidence_snippets=current_snippets,
                    )
                )
                current_text, current_verdict, current_confidence = [], None, 0.5
                current_sources, current_snippets = [], []
            continue
        upper = line.upper()
        if "SUPPORTED" in upper and len(line) < 30:
            current_verdict = Verdict.SUPPORTED
            m = re.search(r"(\d+\.?\d*)%", line)
            if m:
                current_confidence = float(m.group(1)) / 100.0
        elif "REFUTED" in upper and len(line) < 30:
            current_verdict = Verdict.REFUTED
        elif "INSUFFICIENT" in upper and len(line) < 30:
            current_verdict = Verdict.INSUFFICIENT_EVIDENCE
        elif current_verdict and current_text:
            current_text.append(line)
        elif line.startswith("-") or (len(line) > 15 and not current_verdict):
            current_text.append(line.lstrip("- ").lstrip("*. "))

    if current_text and current_verdict:
        results.append(
            Claim(
                id=f"clm_{len(results)}",
                text=" ".join(current_text),
                confidence=current_confidence,
                verdict=current_verdict,
                sources=current_sources,
                evidence_snippets=current_snippets,
            )
        )

    if not results and fallback_claims:
        for c in fallback_claims:
            results.append(c)
    return results


# ─── Presenter ────────────────────────────────────────────────────────────────


def presenter_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    verifier_result = session.get_agent(AgentRole.VERIFIER)
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    claims = verifier_result.claims
    if message and isinstance(message.payload.get("verified_claims"), list):
        claims = [Claim.model_validate(item) for item in message.payload["verified_claims"]]

    findings_ctx = ""
    for c in claims:
        badge = (
            "✅ SUPPORTED"
            if c.verdict == Verdict.SUPPORTED
            else ("❌ REFUTED" if c.verdict == Verdict.REFUTED else "⚠️  INSUFFICIENT_EVIDENCE")
        )
        findings_ctx += f"- **{c.text}**  \n  {badge} · confidence {c.confidence:.0%}\n"
        if c.evidence_snippets:
            for snip in c.evidence_snippets:
                findings_ctx += f"  > {snip}\n"
        if c.sources:
            titles = [get_source_title(s) for s in c.sources]
            findings_ctx += f"  Sources: {', '.join(titles)}\n"
        findings_ctx += "\n"

    user_ctx = (
        f"Original query: {session.query}\n\n"
        f"Verified findings:\n{findings_ctx}\n\n"
        f"Total sources used: "
        f"{len(set(verifier_result.citations + researcher_result.citations))}\n\n"
        "Produce a structured research report in markdown."
    )
    raw = _call_llm(PRESENTER_PROMPT, user_ctx)
    report = extract_report_markdown(raw)
    if not report or report.lstrip().startswith("{"):
        session.agent_results[AgentRole.VERIFIER] = verifier_result.model_copy(
            update={"claims": claims}
        )
        report = build_markdown_report(session)

    return _invoke(
        AgentRole.PRESENTER,
        AgentStatus.COMPLETED,
        "Report ready.",
        raw_content=report,
        citations=aggregate_citations(session.agent_results),
    )
