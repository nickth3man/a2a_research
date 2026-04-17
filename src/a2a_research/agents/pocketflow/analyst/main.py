"""Analyst agent — decomposes research into atomic verifiable claims."""

from __future__ import annotations

import re

from a2a_research.agents.pocketflow.utils import llm as llm_utils
from a2a_research.agents.pocketflow.utils.helpers import (
    extract_claims_from_llm_output,
    normalize_claim_id,
    parse_json_safely,
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
    AnalystOutput,
    Claim,
    ResearchSession,
    Verdict,
)
from a2a_research.providers import ProviderRequestError, parse_structured_response

from .prompt import ANALYST_PROMPT

logger = get_logger(__name__)


def analyst_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    research_summary = (
        str(message.payload.get("research_summary", researcher_result.raw_content))
        if message
        else researcher_result.raw_content
    )
    query = sanitize_query(session.query)
    user_ctx = (
        f"Research summary from Researcher:\n{research_summary}\n\n"
        f"Original query: {query}\n\n"
        "Decompose the query into atomic verifiable claims."
    )
    reporter, step_index, total_steps, granularity = extract_progress_context(message)
    emit = create_substep_emitter(
        reporter, AgentRole.ANALYST, step_index, total_steps, granularity, 2
    )
    logger.info("Analyst start session_id=%s", session.id)
    emit("Calling LLM…", 0)
    try:
        raw = llm_utils.call_llm(ANALYST_PROMPT, user_ctx, stage="analyst")
        claims = parse_claims_from_analyst(raw)
        emit(
            "Parsing claims…",
            1,
            detail=f"{len(claims)} claims extracted" if granularity >= 3 else "",
        )
        status = AgentStatus.COMPLETED
        completion_message = f"Decomposed into {len(claims)} atomic claims."
    except ProviderRequestError as exc:
        raw = ""
        claims = parse_claims_from_analyst(research_summary)
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
    return create_agent_result(
        AgentRole.ANALYST,
        status,
        completion_message,
        raw_content=raw,
        claims=claims,
    )


def parse_claims_from_analyst(raw: str) -> list[Claim]:
    """Parse Analyst LLM output into atomic :class:`Claim` objects with fallbacks."""
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
                raw_text = item.get("text")
                text = raw_text.strip() if isinstance(raw_text, str) else ""
                if not text:
                    continue
                claims.append(
                    Claim(
                        id=normalize_claim_id(item.get("id"), f"clm_{i}"),
                        text=text,
                        verdict=Verdict.INSUFFICIENT_EVIDENCE,
                    )
                )
    return claims
