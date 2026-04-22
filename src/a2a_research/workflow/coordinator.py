"""Run the 5-agent research pipeline via in-process A2A.

Public: :func:`run_research_async`, :func:`run_research_sync`,
:func:`run_research`.

All three return a :class:`ResearchSession` whose ``agent_results`` track
per-role status (for UI timelines), ``sources`` carry the deduplicated URL
set, and ``report`` holds the final :class:`ReportOutput`. On failure,
``error`` is populated and ``final_report`` contains a degraded markdown
explanation.
"""

from __future__ import annotations

import asyncio
from time import perf_counter

from a2a_research.logging.app_logging import get_logger
from a2a_research.models import ResearchSession
from a2a_research.progress import Bus, ProgressQueue
from a2a_research.settings import settings
from a2a_research.workflow.coordinator_drive import drive
from a2a_research.workflow.coordinator_helpers import mark_running_failed

logger = get_logger(__name__)

__all__ = ["run_research", "run_research_async", "run_research_sync"]


async def run_research_async(
    query: str, progress_queue: ProgressQueue | None = None
) -> ResearchSession:
    session = ResearchSession(query=query)
    session.ensure_agent_results()
    started = perf_counter()
    logger.info("workflow start session_id=%s query=%r", session.id, query)

    from a2a_research.a2a import A2AClient, get_registry

    client = A2AClient(get_registry())
    if progress_queue is not None:
        Bus.register(session.id, progress_queue)

    try:
        await asyncio.wait_for(
            drive(session, client, query), timeout=settings.workflow_timeout
        )
    except TimeoutError:
        session.error = (
            f"Workflow timed out after {settings.workflow_timeout:.0f}s "
            "— partial results below."
        )
        mark_running_failed(session)
        logger.warning("workflow timed out session_id=%s", session.id)
    except Exception as exc:
        session.error = str(exc)
        mark_running_failed(session)
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
