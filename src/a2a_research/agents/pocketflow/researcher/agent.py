"""Researcher agent — retrieves RAG chunks and produces a concise summary."""

from __future__ import annotations

from a2a_research import rag
from a2a_research.agents.pocketflow.utils import llm as llm_utils
from a2a_research.agents.pocketflow.utils.fallbacks import fallback_research_summary
from a2a_research.agents.pocketflow.utils.helpers import extract_research_summary
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
    ResearcherOutput,
    ResearchSession,
)
from a2a_research.providers import ProviderRequestError, parse_structured_response

from .prompt import RESEARCHER_PROMPT

logger = get_logger(__name__)


def researcher_invoke(session: ResearchSession, message: A2AMessage | None = None) -> AgentResult:
    query = sanitize_query(
        str(message.payload.get("query", session.query) if message else session.query)
    )
    reporter, step_index, total_steps, granularity = extract_progress_context(message)
    emit = create_substep_emitter(
        reporter, AgentRole.RESEARCHER, step_index, total_steps, granularity, 4
    )
    logger.info("Researcher start session_id=%s query=%r", session.id, query)
    emit("Embedding query…", 0)
    try:
        chunks = rag.retrieve_chunks(query, n_results=10)
    except Exception as exc:
        logger.exception("Researcher RAG retrieval failed session_id=%s", session.id)
        return create_agent_result(
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
        raw = llm_utils.call_llm(
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
        summary = fallback_research_summary(query, chunks)
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
    return create_agent_result(
        AgentRole.RESEARCHER,
        status,
        completion_message or f"Retrieved {len(chunks)} chunks from {len(cited_sources)} sources.",
        raw_content=summary,
        citations=cited_sources,
    )
