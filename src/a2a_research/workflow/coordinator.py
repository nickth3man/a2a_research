"""Run the 5-agent research pipeline via in-process A2A.

Public: :func:`run_research_async`, :func:`run_research_sync`, :func:`run_research`.

All three return a :class:`ResearchSession` whose ``agent_results`` track
per-role status (for UI timelines), ``sources`` carry the deduplicated URL set,
and ``report`` holds the final :class:`ReportOutput`. On failure, ``error`` is
populated and ``final_report`` contains a degraded markdown explanation.
"""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from a2a.types import TaskState
from pydantic import ValidationError

from a2a_research.a2a import (
    A2AClient,
    extract_data_payload_or_warn,
    get_registry,
)
from a2a_research.app_logging import get_logger
from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ReportOutput,
    ResearchSession,
    WebSource,
)
from a2a_research.progress import Bus, ProgressPhase, ProgressQueue, emit
from a2a_research.settings import settings
from a2a_research.tools import PageContent, WebHit

logger = get_logger(__name__)

__all__ = ["run_research", "run_research_async", "run_research_sync"]

_TOTAL_STEPS = 5
_STEP_INDEX = {
    AgentRole.PLANNER: 0,
    AgentRole.SEARCHER: 1,
    AgentRole.READER: 2,
    AgentRole.FACT_CHECKER: 3,
    AgentRole.SYNTHESIZER: 4,
}


async def run_research_async(
    query: str, progress_queue: ProgressQueue | None = None
) -> ResearchSession:
    session = ResearchSession(query=query)
    session.ensure_agent_results()
    started = perf_counter()
    logger.info("workflow start session_id=%s query=%r", session.id, query)

    client = A2AClient(get_registry())
    if progress_queue is not None:
        Bus.register(session.id, progress_queue)

    try:
        await asyncio.wait_for(
            _drive(session, client, query), timeout=settings.workflow_timeout
        )
    except (
        TimeoutError
    ):  # asyncio.TimeoutError is the same class on Python 3.11+
        session.error = f"Workflow timed out after {settings.workflow_timeout:.0f}s — partial results below."
        _mark_running_failed(session)
        logger.warning("workflow timed out session_id=%s", session.id)
    except Exception as exc:
        session.error = str(exc)
        _mark_running_failed(session)
        logger.exception("workflow failed session_id=%s", session.id)

    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "workflow done session_id=%s elapsed_ms=%.1f error=%s",
        session.id,
        elapsed_ms,
        session.error,
    )
    if progress_queue is not None:
        progress_queue.put_nowait(None)
        Bus.unregister(session.id)
    return session


def run_research_sync(query: str) -> ResearchSession:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        msg = (
            "run_research_sync cannot be called from a running event loop; "
            "use run_research_async instead."
        )
        raise RuntimeError(msg)
    return asyncio.run(run_research_async(query))


def run_research(query: str) -> ResearchSession:
    """Alias for :func:`run_research_sync` (legacy name)."""
    return run_research_sync(query)


async def _drive(
    session: ResearchSession, client: A2AClient, query: str
) -> None:
    _emit_role_event(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_STARTED,
        "planner_started",
    )
    _set_status(
        session, AgentRole.PLANNER, AgentStatus.RUNNING, "Decomposing query…"
    )
    plan_task = await client.send(
        AgentRole.PLANNER,
        payload={"query": query, "session_id": session.id},
    )
    plan = _payload(plan_task)
    plan_failed = _task_failed(plan_task)
    claims: list[Claim] = [
        c
        for c in (_coerce_claim(item) for item in (plan.get("claims") or []))
        if c is not None
    ]
    seed_queries = [
        str(q) for q in (plan.get("seed_queries") or []) if isinstance(q, str)
    ]
    session.claims = claims
    _set_status(
        session,
        AgentRole.PLANNER,
        AgentStatus.FAILED if plan_failed else AgentStatus.COMPLETED,
        (
            "Failed to decompose query."
            if plan_failed
            else f"Extracted {len(claims)} claim(s)."
        ),
    )
    if plan_failed:
        _emit_role_event(
            session.id,
            AgentRole.PLANNER,
            ProgressPhase.STEP_FAILED,
            "planner_failed",
        )
        session.error = "Planner failed to decompose query."
        _set_status(
            session,
            AgentRole.SEARCHER,
            AgentStatus.FAILED,
            "Skipped: planner failed.",
        )
        _set_status(
            session,
            AgentRole.READER,
            AgentStatus.FAILED,
            "Skipped: planner failed.",
        )
        _set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Skipped: planner failed.",
        )
        _set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: planner failed.",
        )
        session.report = None
        session.final_report = _planner_failed_report(query)
        return
    _emit_role_event(
        session.id,
        AgentRole.PLANNER,
        ProgressPhase.STEP_COMPLETED,
        "planner_completed",
    )

    _set_status(session, AgentRole.SEARCHER, AgentStatus.RUNNING, "Searching…")
    _emit_role_event(
        session.id,
        AgentRole.SEARCHER,
        ProgressPhase.STEP_STARTED,
        "searcher_started",
    )
    search_task = await client.send(
        AgentRole.SEARCHER,
        payload={"queries": seed_queries, "session_id": session.id},
        from_role=AgentRole.PLANNER,
    )
    search_data = _payload(search_task)
    search_failed = _task_failed(search_task)
    raw_hits = search_data.get("hits") or []
    hits = [_coerce_web_hit(h) for h in raw_hits]
    hits = [h for h in hits if h is not None]
    search_errors = [
        str(e) for e in (search_data.get("errors") or []) if isinstance(e, str)
    ]

    if search_failed or not hits:
        reason = " | ".join(search_errors) or "web search produced no results."
        _set_status(
            session,
            AgentRole.SEARCHER,
            AgentStatus.FAILED,
            f"Search failed: {reason}",
        )
        _set_status(
            session,
            AgentRole.READER,
            AgentStatus.FAILED,
            "Skipped: search failed.",
        )
        _set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Skipped: no evidence.",
        )
        _set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: no verified evidence to synthesize.",
        )
        _emit_role_event(
            session.id,
            AgentRole.SEARCHER,
            ProgressPhase.STEP_FAILED,
            "searcher_failed",
        )
        session.error = "Research pipeline aborted: " + reason
        session.final_report = _error_report(query, reason, search_errors)
        return

    urls = [h.url for h in hits[:6]]
    _set_status(
        session,
        AgentRole.SEARCHER,
        AgentStatus.COMPLETED,
        f"{len(hits)} hit(s), {len(urls)} URL(s) selected.",
    )
    _emit_role_event(
        session.id,
        AgentRole.SEARCHER,
        ProgressPhase.STEP_COMPLETED,
        "searcher_completed",
    )

    _set_status(
        session, AgentRole.READER, AgentStatus.RUNNING, "Reading pages…"
    )
    _emit_role_event(
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
    read_data = _payload(read_task)
    read_failed = _task_failed(read_task)
    raw_pages = read_data.get("pages") or []
    pages = [_coerce_page_content(p) for p in raw_pages]
    pages = [p for p in pages if p is not None]
    successful_pages = [p for p in pages if not p.error and p.markdown]
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
        _set_status(session, AgentRole.READER, AgentStatus.FAILED, reason)
        _set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Skipped: no evidence.",
        )
        _set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: no verified evidence to synthesize.",
        )
        _emit_role_event(
            session.id,
            AgentRole.READER,
            ProgressPhase.STEP_FAILED,
            "reader_failed",
        )
        session.error = "Research pipeline aborted: " + reason
        session.final_report = _error_report(query, reason, [])
        return

    _set_status(
        session,
        AgentRole.READER,
        AgentStatus.COMPLETED,
        f"{len(successful_pages)} page(s) extracted.",
    )
    _emit_role_event(
        session.id,
        AgentRole.READER,
        ProgressPhase.STEP_COMPLETED,
        "reader_completed",
    )

    _set_status(
        session,
        AgentRole.FACT_CHECKER,
        AgentStatus.RUNNING,
        "Verifying claims…",
    )
    _emit_role_event(
        session.id,
        AgentRole.FACT_CHECKER,
        ProgressPhase.STEP_STARTED,
        "fact_checker_started",
    )
    fc_task = await client.send(
        AgentRole.FACT_CHECKER,
        payload={
            "session_id": session.id,
            "query": query,
            "claims": [c.model_dump(mode="json") for c in claims],
            "evidence": [p.model_dump(mode="json") for p in successful_pages],
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        from_role=AgentRole.READER,
    )
    fc_data = _payload(fc_task)
    verified: list[Claim] = [
        c
        for c in (
            _coerce_claim(item)
            for item in (fc_data.get("verified_claims") or [])
        )
        if c is not None
    ]
    fc_failed = _task_failed(fc_task)

    session.claims = verified or claims
    session.sources = sources

    if fc_failed:
        _emit_role_event(
            session.id,
            AgentRole.FACT_CHECKER,
            ProgressPhase.STEP_FAILED,
            "fact_checker_failed",
        )
        _set_status(
            session,
            AgentRole.FACT_CHECKER,
            AgentStatus.FAILED,
            "Failed to verify claims.",
        )
        _set_status(
            session,
            AgentRole.SYNTHESIZER,
            AgentStatus.FAILED,
            "Skipped: verification failed.",
        )
        session.error = "FactChecker failed to verify claims."
        session.report = None
        session.final_report = _error_report(query, "FactChecker failed.", [])
        return

    _set_status(
        session,
        AgentRole.FACT_CHECKER,
        AgentStatus.COMPLETED,
        f"Verified {len(verified)} claim(s).",
    )
    _emit_role_event(
        session.id,
        AgentRole.FACT_CHECKER,
        ProgressPhase.STEP_COMPLETED,
        "fact_checker_completed",
    )

    _set_status(
        session, AgentRole.SYNTHESIZER, AgentStatus.RUNNING, "Writing report…"
    )
    _emit_role_event(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_STARTED,
        "synthesizer_started",
    )
    syn_task = await client.send(
        AgentRole.SYNTHESIZER,
        payload={
            "session_id": session.id,
            "query": query,
            "verified_claims": [
                c.model_dump(mode="json") for c in (verified or claims)
            ],
            "sources": [s.model_dump(mode="json") for s in sources],
        },
        from_role=AgentRole.FACT_CHECKER,
    )
    syn_data = _payload(syn_task)
    syn_failed = _task_failed(syn_task)
    report = _coerce_report(syn_data.get("report"))
    session.report = report
    session.final_report = report.to_markdown() if report else ""
    _set_status(
        session,
        AgentRole.SYNTHESIZER,
        AgentStatus.FAILED if syn_failed else AgentStatus.COMPLETED,
        "Failed to synthesize report."
        if syn_failed
        else "Report synthesized.",
    )
    if syn_failed:
        _emit_role_event(
            session.id,
            AgentRole.SYNTHESIZER,
            ProgressPhase.STEP_FAILED,
            "synthesizer_failed",
        )
        session.error = (
            session.error or "Synthesizer failed to produce a report."
        )
    else:
        _emit_role_event(
            session.id,
            AgentRole.SYNTHESIZER,
            ProgressPhase.STEP_COMPLETED,
            "synthesizer_completed",
        )


def _task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return state == TaskState.TASK_STATE_FAILED


def _planner_failed_report(query: str) -> str:
    return "\n".join(
        [
            "# Planner failed",
            "",
            f"**Query:** {query}",
            "",
            "The planner could not decompose this query into claims, so the pipeline stopped.",
            "",
        ]
    )


def _error_report(query: str, reason: str, errors: list[str]) -> str:
    lines = [
        "# Research unavailable",
        "",
        f"**Query:** {query}",
        "",
        "The fact-checking pipeline could not gather web evidence, so no verified",
        "report was produced. The Synthesizer was skipped deliberately to avoid",
        "presenting unverified claims as fact.",
        "",
        "## Reason",
        "",
        reason,
    ]
    if errors:
        lines.extend(["", "## Provider-level errors", ""])
        lines.extend(f"- {err}" for err in errors)
    lines.extend(["", "## How to fix", ""])
    lines.append(
        "- Set `TAVILY_API_KEY` in `.env` (https://tavily.com/) and `BRAVE_API_KEY` "
        "(https://api-dashboard.search.brave.com/) if search providers are misconfigured."
    )
    lines.append(
        "- Wait and retry if DuckDuckGo rate-limited the request, or run "
        "behind a different egress."
    )
    lines.append(
        "- Re-run after verifying network connectivity to the search endpoints."
    )
    return "\n".join(lines) + "\n"


def _payload(task: Any) -> dict[str, Any]:
    if task is None:
        return {}
    return extract_data_payload_or_warn(task)


def _set_status(
    session: ResearchSession,
    role: AgentRole,
    status: AgentStatus,
    message: str,
) -> None:
    session.agent_results[role] = AgentResult(
        role=role, status=status, message=message
    )


def _emit_role_event(
    session_id: str,
    role: AgentRole,
    phase: ProgressPhase,
    label: str,
    detail: str = "",
) -> None:
    emit(
        session_id,
        phase,
        role,
        _STEP_INDEX[role],
        _TOTAL_STEPS,
        label,
        detail=detail,
    )


def _mark_running_failed(session: ResearchSession) -> None:
    for role, result in list(session.agent_results.items()):
        if result.status == AgentStatus.RUNNING:
            session.agent_results[role] = result.model_copy(
                update={"status": AgentStatus.FAILED, "message": "Aborted."}
            )


def _coerce_claim(raw: Any) -> Claim | None:
    if isinstance(raw, Claim):
        return raw
    if isinstance(raw, dict):
        try:
            return Claim.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce claim from payload: %s", exc)
            return None
    return None


def _coerce_report(raw: Any) -> ReportOutput | None:
    if isinstance(raw, ReportOutput):
        return raw
    if isinstance(raw, dict):
        try:
            return ReportOutput.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce report from payload: %s", exc)
            return None
    return None


def _coerce_web_hit(raw: Any) -> WebHit | None:
    if isinstance(raw, WebHit):
        return raw
    if isinstance(raw, dict):
        try:
            return WebHit.model_validate(raw)
        except ValidationError as exc:
            logger.warning("Failed to coerce WebHit from payload: %s", exc)
            return None
    return None


def _coerce_page_content(raw: Any) -> PageContent | None:
    if isinstance(raw, PageContent):
        return raw
    if isinstance(raw, dict):
        try:
            return PageContent.model_validate(raw)
        except ValidationError as exc:
            logger.warning(
                "Failed to coerce PageContent from payload: %s", exc
            )
            return None
    return None
