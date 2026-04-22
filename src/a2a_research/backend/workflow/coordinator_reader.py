"""Reader step for the coordinator workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.backend.core.models import AgentRole, AgentStatus, WebSource
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.coordinator_helpers import (
    coerce_page_content,
    emit_role_event,
    error_report,
    payload,
    set_status,
    task_failed,
)

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import Claim, ResearchSession
    from a2a_research.backend.tools import PageContent, WebHit


async def run_reader_step(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    claims: list[Claim],
    hits: list[WebHit],
) -> tuple[list[WebSource], list[PageContent], bool]:
    """Run reader and return (sources, successful_pages, should_abort)."""
    urls = [h.url for h in hits[:6]]
    set_status(
        session, AgentRole.READER, AgentStatus.RUNNING, "Reading pages…"
    )
    emit_role_event(
        session.id,
        AgentRole.READER,
        ProgressPhase.STEP_STARTED,
        "reader_started",
    )
    read_task = await client.send(
        AgentRole.READER,
        payload={
            "urls": urls,
            "session_id": session.id,
            "claims": [c.model_dump(mode="json") for c in claims],
        },
        from_role=AgentRole.SEARCHER,
    )
    read_data = payload(read_task)
    read_failed = task_failed(read_task)
    raw_pages = read_data.get("pages") or []
    pages_maybe = [coerce_page_content(p) for p in raw_pages]
    pages: list[PageContent] = [p for p in pages_maybe if p is not None]
    successful_pages: list[PageContent] = [
        p for p in pages if not p.error and p.markdown
    ]
    sources: list[WebSource] = [
        WebSource(
            url=p.url,
            title=p.title or p.url,
            excerpt=(p.markdown[:280] if p.markdown else ""),
        )
        for p in successful_pages
    ]

    if read_failed or not successful_pages:
        reason = "All URLs failed to extract."
        set_status(session, AgentRole.READER, AgentStatus.FAILED, reason)
        set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Skipped: no evidence.",
        )
        set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: no verified evidence to synthesize.",
        )
        emit_role_event(
            session.id,
            AgentRole.READER,
            ProgressPhase.STEP_FAILED,
            "reader_failed",
        )
        session.error = "Research pipeline aborted: " + reason
        session.final_report = error_report(query, reason, [])
        return sources, successful_pages, True

    set_status(
        session,
        AgentRole.READER,
        AgentStatus.COMPLETED,
        f"{len(successful_pages)} page(s) extracted.",
    )
    emit_role_event(
        session.id,
        AgentRole.READER,
        ProgressPhase.STEP_COMPLETED,
        "reader_completed",
    )
    return sources, successful_pages, False
