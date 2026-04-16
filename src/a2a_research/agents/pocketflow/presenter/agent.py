"""Presenter agent — synthesises verified claims into a final markdown report."""

from __future__ import annotations

from pydantic import ValidationError

from a2a_research import rag
from a2a_research.agents.pocketflow.utils import llm as llm_utils
from a2a_research.agents.pocketflow.utils.helpers import (
    aggregate_citations,
    build_markdown_report,
    extract_report_markdown,
)
from a2a_research.agents.pocketflow.utils.progress import (
    create_substep_emitter,
    extract_progress_context,
)
from a2a_research.agents.pocketflow.utils.results import create_agent_result
from a2a_research.agents.pocketflow.utils.sanitize import sanitize_query
from a2a_research.app_logging import get_logger
from a2a_research.models import (
    A2AMessage,
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    PresenterOutput,
    ResearchSession,
    Verdict,
)
from a2a_research.providers import ProviderRequestError, parse_structured_response

from .prompt import PRESENTER_PROMPT

logger = get_logger(__name__)


def _format_findings(claims: list[Claim]) -> str:
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
            titles = [rag.get_source_title(s) for s in c.sources]
            findings_ctx += f"  Sources: {', '.join(titles)}\n"
        findings_ctx += "\n"
    return findings_ctx


def presenter_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    verifier_result = session.get_agent(AgentRole.VERIFIER)
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    claims = verifier_result.claims
    if message and isinstance(message.payload.get("verified_claims"), list):
        try:
            claims = [Claim.model_validate(item) for item in message.payload["verified_claims"]]
        except (ValidationError, TypeError, ValueError) as exc:
            logger.warning(
                "Presenter received malformed verified_claims; falling back to verifier result "
                "session_id=%s error=%s",
                session.id,
                exc,
            )
            claims = verifier_result.claims

    findings_ctx = _format_findings(claims)

    query = sanitize_query(session.query)
    user_ctx = (
        f"Original query: {query}\n\n"
        f"Verified findings:\n{findings_ctx}\n\n"
        f"Total sources used: "
        f"{len(set(verifier_result.citations + researcher_result.citations))}\n\n"
        "Produce a structured research report in markdown."
    )
    logger.info("Presenter start session_id=%s verified_claims=%s", session.id, len(claims))
    reporter, step_index, total_steps, granularity = extract_progress_context(message)
    emit = create_substep_emitter(
        reporter, AgentRole.PRESENTER, step_index, total_steps, granularity, 2
    )
    emit("Calling LLM…", 0)
    try:
        raw = llm_utils.call_llm(PRESENTER_PROMPT, user_ctx, stage="presenter")
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
    return create_agent_result(
        AgentRole.PRESENTER,
        AgentStatus.COMPLETED,
        result_message,
        raw_content=report,
        citations=aggregate_citations(session.agent_results),
    )
