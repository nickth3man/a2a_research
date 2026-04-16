"""Agent implementations for the 4-agent research pipeline.

Order: Researcher → Analyst → Verifier → Presenter. Each step:

- Reads the shared :class:`~a2a_research.models.ResearchSession` and prior outputs.
- Calls the LLM (or deterministic fallback on :class:`~a2a_research.providers.ProviderRequestError`).
- Writes its :class:`~a2a_research.models.AgentResult` back into ``session.agent_results``.

Handlers are registered in :mod:`a2a_research.agents.registry` and invoked through
the in-process A2A layer from :mod:`a2a_research.workflow.nodes`.
"""

from __future__ import annotations

import json
import re
from time import perf_counter
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from a2a_research.agents.registry import (
    AgentRegistry as AgentRegistry,
)
from a2a_research.agents.registry import (
    AgentSpec as AgentSpec,
)
from a2a_research.agents.registry import (
    get_agent_handler as get_agent_handler,
)
from a2a_research.agents.registry import (
    get_agent_spec as get_agent_spec,
)
from a2a_research.agents.registry import (
    get_registry as get_registry,
)
from a2a_research.agents.registry import (
    register_agent as register_agent,
)
from a2a_research.app_logging import get_logger
from a2a_research.helpers import (
    aggregate_citations,
    build_markdown_report,
    extract_claims_from_llm_output,
    extract_report_markdown,
    extract_research_summary,
    normalize_claim_id,
    parse_json_safely,
)
from a2a_research.models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    AnalystOutput,
    Claim,
    PresenterOutput,
    ResearcherOutput,
    ResearchSession,
    RetrievedChunk,
    Verdict,
    VerifierOutput,
)
from a2a_research.progress import (
    ProgressEvent,
    ProgressGranularity,
    ProgressPhase,
    ProgressReporter,
)
from a2a_research.prompts import (
    ANALYST_PROMPT,
    PRESENTER_PROMPT,
    RESEARCHER_PROMPT,
    VERIFIER_PROMPT,
)
from a2a_research.providers import ProviderRequestError, get_llm, parse_structured_response
from a2a_research.rag import get_source_title, retrieve_chunks

logger = get_logger(__name__)


def _extract_progress_context(
    message: A2AMessage | None,
) -> tuple[ProgressReporter | None, int, int, int]:
    """Extract (reporter, step_index, total_steps, granularity) from a message payload."""
    if message is None:
        return None, 0, 4, 1
    reporter: ProgressReporter | None = message.payload.get("__progress_reporter__")
    ctx: dict[str, Any] = message.payload.get("progress_context") or {}
    return (
        reporter,
        int(ctx.get("step_index", 0)),
        int(ctx.get("total_steps", 4)),
        int(ctx.get("granularity", 1)),
    )


def _create_substep_emitter(
    reporter: ProgressReporter | None,
    role: AgentRole,
    step_index: int,
    total_steps: int,
    granularity: int,
    substep_total: int,
) -> Callable[..., None]:
    """Return a callable that emits a STEP_SUBSTEP event when granularity allows it."""

    def emit(label: str, substep_index: int, min_granularity: int = 2, detail: str = "") -> None:
        if reporter is None or granularity < min_granularity:
            return
        reporter(
            ProgressEvent(
                phase=ProgressPhase.STEP_SUBSTEP,
                role=role,
                step_index=step_index,
                total_steps=total_steps,
                substep_label=label,
                substep_index=substep_index,
                substep_total=substep_total,
                granularity=ProgressGranularity(min(granularity, 3)),
                detail=detail,
            )
        )

    return emit


def _call_llm(system_prompt: str, user_content: str, *, stage: str) -> str:
    logger.info(
        "LLM stage=%s start system_chars=%s user_chars=%s",
        stage,
        len(system_prompt),
        len(user_content),
    )
    started_at = perf_counter()
    llm = get_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        response = llm.invoke(messages)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception("LLM stage=%s failed elapsed_ms=%.1f", stage, elapsed_ms)
        raise
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("LLM stage=%s completed elapsed_ms=%.1f", stage, elapsed_ms)
    return str(response.content) if hasattr(response, "content") else str(response)


def _create_agent_result(
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


def _fallback_research_summary(query: str, chunks: list[Any]) -> str:
    if not chunks:
        return f"No retrieved evidence was available for the query: {query}"

    summary_lines = [f"Fallback research summary for query: {query}"]
    for rc in chunks[:3]:
        summary_lines.append(
            f"- source={rc.chunk.source} score={rc.score:.3f}: {rc.chunk.content[:180].strip()}"
        )
    return "\n".join(summary_lines)


def _fallback_verified_claims(claims: list[Claim], reason: str) -> list[Claim]:
    return [
        claim.model_copy(
            update={
                "verdict": Verdict.INSUFFICIENT_EVIDENCE,
                "confidence": 0.0,
                "sources": [],
                "evidence_snippets": [reason],
            }
        )
        for claim in claims
    ]


def researcher_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    query = str(message.payload.get("query", session.query) if message else session.query)
    reporter, step_index, total_steps, granularity = _extract_progress_context(message)
    emit = _create_substep_emitter(
        reporter, AgentRole.RESEARCHER, step_index, total_steps, granularity, 4
    )
    logger.info("Researcher start session_id=%s query=%r", session.id, query)
    emit("Embedding query…", 0)
    try:
        chunks = retrieve_chunks(query, n_results=10)
    except Exception as exc:
        logger.exception("Researcher RAG retrieval failed session_id=%s", session.id)
        return _create_agent_result(
            AgentRole.RESEARCHER, AgentStatus.FAILED, f"RAG retrieval failed: {exc}"
        )

    chunk_detail = f"{len(chunks)} chunks found" if granularity >= 3 else ""
    emit("Querying ChromaDB…", 1, detail=chunk_detail)

    max_sources = 10
    user_ctx = f"Research query: {query}\n\nRelevant corpus chunks (id, source, score, content):\n"
    for rc in chunks:
        user_ctx += (
            f"[{rc.chunk.id}] source={rc.chunk.source} "
            f"score={rc.score:.3f}\n{rc.chunk.content[:300]}\n\n"
        )

    user_ctx += "\nProduce your research summary based on the above chunks."
    emit("Calling LLM…", 2)
    try:
        raw = _call_llm(
            RESEARCHER_PROMPT.format(max_sources=max_sources), user_ctx, stage="researcher"
        )
        emit("Parsing result…", 3)
        structured = parse_structured_response(raw, ResearcherOutput)
        summary = (
            structured.research_summary.strip()
            if structured and structured.research_summary.strip()
            else extract_research_summary(raw)
        )
        status = AgentStatus.COMPLETED
        completion_message = None
    except ProviderRequestError as exc:
        raw = ""
        summary = _fallback_research_summary(query, chunks)
        status = AgentStatus.COMPLETED
        completion_message = f"Retrieved evidence via fallback after provider error: {exc}"
        logger.warning(
            "Researcher falling back to deterministic summary session_id=%s", session.id
        )

    cited_sources = list({rc.chunk.source for rc in chunks})
    session.retrieved_chunks = chunks
    session.source_titles.update(
        {rc.chunk.source: str(rc.chunk.metadata.get("title") or rc.chunk.source) for rc in chunks}
    )
    logger.info(
        "Researcher completed session_id=%s chunks=%s unique_sources=%s",
        session.id,
        len(chunks),
        len(cited_sources),
    )
    return _create_agent_result(
        AgentRole.RESEARCHER,
        status,
        completion_message or f"Retrieved {len(chunks)} chunks from {len(cited_sources)} sources.",
        raw_content=summary,
        citations=cited_sources,
    )


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
    reporter, step_index, total_steps, granularity = _extract_progress_context(message)
    emit = _create_substep_emitter(
        reporter, AgentRole.ANALYST, step_index, total_steps, granularity, 2
    )
    logger.info("Analyst start session_id=%s", session.id)
    emit("Calling LLM…", 0)
    try:
        raw = _call_llm(ANALYST_PROMPT, user_ctx, stage="analyst")
        claims = _parse_claims_from_analyst(raw)
        emit(
            "Parsing claims…",
            1,
            detail=f"{len(claims)} claims extracted" if granularity >= 3 else "",
        )
        status = AgentStatus.COMPLETED
        completion_message = f"Decomposed into {len(claims)} atomic claims."
    except ProviderRequestError as exc:
        raw = ""
        claims = _parse_claims_from_analyst(research_summary)
        emit(
            "Parsing claims…",
            1,
            detail=f"{len(claims)} claims extracted" if granularity >= 3 else "",
        )
        status = AgentStatus.COMPLETED if claims else AgentStatus.FAILED
        completion_message = (
            f"Decomposed into {len(claims)} atomic claims via fallback after provider error."
            if claims
            else f"Analyst provider unavailable: {exc}"
        )
        logger.warning(
            "Analyst falling back to deterministic claim parsing session_id=%s claims=%s",
            session.id,
            len(claims),
        )
    logger.info("Analyst completed session_id=%s claim_count=%s", session.id, len(claims))
    return _create_agent_result(
        AgentRole.ANALYST,
        status,
        completion_message,
        raw_content=raw,
        claims=claims,
    )


def _parse_claims_from_analyst(raw: str) -> list[Claim]:
    structured = parse_structured_response(raw, AnalystOutput)
    if structured and structured.atomic_claims:
        return [
            claim.model_copy(update={"id": normalize_claim_id(claim.id, f"clm_{i}")})
            for i, claim in enumerate(structured.atomic_claims)
        ]

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
                        id=normalize_claim_id(item.get("id"), f"clm_{i}"),
                        text=item.get("text", ""),
                        verdict=Verdict.INSUFFICIENT_EVIDENCE,
                    )
                )
    return claims


def verifier_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    analyst_result = session.get_agent(AgentRole.ANALYST)
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    if message and isinstance(message.payload.get("claims"), list):
        claims = [Claim.model_validate(item) for item in message.payload["claims"]]
    else:
        claims = analyst_result.claims
    query = str(message.payload.get("query", session.query) if message else session.query)

    reporter, step_index, total_steps, granularity = _extract_progress_context(message)
    emit = _create_substep_emitter(
        reporter, AgentRole.VERIFIER, step_index, total_steps, granularity, 4
    )

    logger.info("Verifier start session_id=%s input_claims=%s", session.id, len(claims))
    payload_chunks = message.payload.get("retrieved_chunks") if message else None
    if isinstance(payload_chunks, list):
        chunks = [RetrievedChunk.model_validate(item) for item in payload_chunks]
        emit("Loading evidence corpus…", 0)
        chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
        emit("Evidence ready…", 1, detail=chunk_detail)
    elif session.retrieved_chunks:
        chunks = session.retrieved_chunks
        emit("Using session evidence…", 0)
        chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
        emit("Evidence ready…", 1, detail=chunk_detail)
    else:
        emit("Embedding query…", 0)
        try:
            chunks = retrieve_chunks(query, n_results=10)
        except Exception:
            logger.exception("Verifier RAG retrieval failed session_id=%s", session.id)
            chunks = []
        chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
        emit("Querying ChromaDB…", 1, detail=chunk_detail)
    session.retrieved_chunks = chunks

    evidence_ctx = ""
    for rc in chunks:
        evidence_ctx += f"[{rc.chunk.source}] score={rc.score:.3f}\n{rc.chunk.content}\n\n"

    claims_ctx = "\n".join(f"- [{c.id}] {c.text}" for c in claims)

    user_ctx = (
        f"Claims to verify:\n{claims_ctx}\n\n"
        f"Evidence from corpus:\n{evidence_ctx}\n\n"
        "Assign verdicts and confidence scores to each claim."
    )
    emit("Calling LLM…", 2)
    try:
        raw = _call_llm(VERIFIER_PROMPT, user_ctx, stage="verifier")
        verified = _parse_verified_claims(raw, claims)
        emit(
            "Parsing verdicts…",
            3,
            detail=(f"{len(verified)} claims \u00b7 evidence matched" if granularity >= 3 else ""),
        )
        completion_message = f"Verified {len(verified)} claims."
    except ProviderRequestError as exc:
        raw = ""
        verified = _fallback_verified_claims(claims, f"Verification unavailable: {exc}")
        emit(
            "Parsing verdicts…",
            3,
            detail=(f"{len(verified)} claims \u00b7 evidence matched" if granularity >= 3 else ""),
        )
        completion_message = (
            f"Verification degraded after provider error; marked {len(verified)} claims as "
            "INSUFFICIENT_EVIDENCE."
        )
        logger.warning(
            "Verifier falling back to insufficient-evidence claims session_id=%s claims=%s",
            session.id,
            len(verified),
        )
    logger.info(
        "Verifier completed session_id=%s evidence_chunks=%s verified_claims=%s",
        session.id,
        len(chunks),
        len(verified),
    )
    return _create_agent_result(
        AgentRole.VERIFIER,
        AgentStatus.COMPLETED,
        completion_message,
        raw_content=raw,
        claims=verified,
        citations=researcher_result.citations,
    )


def _parse_verified_claims(raw: str, fallback_claims: list[Claim]) -> list[Claim]:
    structured = parse_structured_response(raw, VerifierOutput)
    if structured and structured.verified_claims:
        return [
            claim.model_copy(update={"id": normalize_claim_id(claim.id, f"clm_{i}")})
            for i, claim in enumerate(structured.verified_claims)
        ]

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
                    id=normalize_claim_id(item.get("id"), f"clm_{len(verified)}"),
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
    logger.info("Presenter start session_id=%s verified_claims=%s", session.id, len(claims))
    reporter, step_index, total_steps, granularity = _extract_progress_context(message)
    emit = _create_substep_emitter(
        reporter, AgentRole.PRESENTER, step_index, total_steps, granularity, 2
    )
    emit("Calling LLM…", 0)
    try:
        raw = _call_llm(PRESENTER_PROMPT, user_ctx, stage="presenter")
        structured = parse_structured_response(raw, PresenterOutput)
        report = (
            structured.report.strip()
            if structured and structured.report.strip()
            else extract_report_markdown(raw)
        )
        result_message = "Report ready."
        if not report or report.lstrip().startswith("{"):
            session.agent_results[AgentRole.VERIFIER] = verifier_result.model_copy(
                update={"claims": claims}
            )
            report = build_markdown_report(session)
            result_message = "Report ready via deterministic fallback."
            logger.info(
                "Presenter fell back to deterministic markdown report session_id=%s", session.id
            )
        emit(
            "Extracting report…",
            1,
            detail=f"{len(report.split())} words" if granularity >= 3 else "",
        )
    except ProviderRequestError as exc:
        raw = ""
        session.agent_results[AgentRole.VERIFIER] = verifier_result.model_copy(
            update={"claims": claims}
        )
        report = build_markdown_report(session)
        emit(
            "Extracting report…",
            1,
            detail=f"{len(report.split())} words (fallback)" if granularity >= 3 else "",
        )
        result_message = f"Report ready via fallback after provider error: {exc}"
        logger.warning("Presenter falling back to deterministic report session_id=%s", session.id)

    logger.info("Presenter completed session_id=%s report_chars=%s", session.id, len(report))
    return _create_agent_result(
        AgentRole.PRESENTER,
        AgentStatus.COMPLETED,
        result_message,
        raw_content=report,
        citations=aggregate_citations(session.agent_results),
    )


__all__ = [
    "AgentRegistry",
    "AgentSpec",
    "analyst_invoke",
    "get_agent_handler",
    "get_agent_spec",
    "get_registry",
    "presenter_invoke",
    "register_agent",
    "researcher_invoke",
    "verifier_invoke",
]
