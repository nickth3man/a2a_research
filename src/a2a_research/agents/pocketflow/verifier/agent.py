"""Verifier agent — assigns verdicts to atomic claims using retrieved evidence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research import rag
from a2a_research.agents.pocketflow.utils import llm as llm_utils
from a2a_research.agents.pocketflow.utils.fallbacks import fallback_verified_claims
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
    ResearchSession,
    RetrievedChunk,
)
from a2a_research.providers import ProviderRequestError

from .parsers import parse_verified_claims
from .prompt import VERIFIER_PROMPT

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)


def _load_evidence_chunks(
    session: ResearchSession,
    message: A2AMessage | None,
    query: str,
    emit: Callable[..., None],
    granularity: int,
) -> list[RetrievedChunk]:
    payload_chunks = message.payload.get("retrieved_chunks") if message else None
    if isinstance(payload_chunks, list):
        chunks = [RetrievedChunk.model_validate(item) for item in payload_chunks]
        emit("Loading evidence corpus…", 0)
        chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
        emit("Evidence ready…", 1, detail=chunk_detail)
        return chunks
    if session.retrieved_chunks:
        chunks = session.retrieved_chunks
        emit("Using session evidence…", 0)
        chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
        emit("Evidence ready…", 1, detail=chunk_detail)
        return chunks
    emit("Embedding query…", 0)
    try:
        chunks = rag.retrieve_chunks(query, n_results=10)
    except Exception:
        logger.exception("Verifier RAG retrieval failed session_id=%s", session.id)
        chunks = []
    chunk_detail = f"{len(chunks)} chunks" if granularity >= 3 else ""
    emit("Querying ChromaDB…", 1, detail=chunk_detail)
    return chunks


def verifier_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    analyst_result = session.get_agent(AgentRole.ANALYST)
    researcher_result = session.get_agent(AgentRole.RESEARCHER)
    if message and isinstance(message.payload.get("claims"), list):
        claims = [Claim.model_validate(item) for item in message.payload["claims"]]
    else:
        claims = analyst_result.claims
    query = sanitize_query(
        str(message.payload.get("query", session.query) if message else session.query)
    )

    reporter, step_index, total_steps, granularity = extract_progress_context(message)
    emit = create_substep_emitter(
        reporter, AgentRole.VERIFIER, step_index, total_steps, granularity, 4
    )

    logger.info("Verifier start session_id=%s input_claims=%s", session.id, len(claims))
    chunks = _load_evidence_chunks(session, message, query, emit, granularity)
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
        raw = llm_utils.call_llm(VERIFIER_PROMPT, user_ctx, stage="verifier")
        verified = parse_verified_claims(raw, claims)
        emit(
            "Parsing verdicts…",
            3,
            detail=(f"{len(verified)} claims · evidence matched" if granularity >= 3 else ""),
        )
        completion_message = f"Verified {len(verified)} claims."
    except ProviderRequestError as exc:
        raw = ""
        verified = fallback_verified_claims(claims, f"Verification unavailable: {exc}")
        emit(
            "Parsing verdicts…",
            3,
            detail=(f"{len(verified)} claims · evidence matched" if granularity >= 3 else ""),
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
    return create_agent_result(
        AgentRole.VERIFIER,
        AgentStatus.COMPLETED,
        completion_message,
        raw_content=raw,
        claims=verified,
        citations=researcher_result.citations,
    )
