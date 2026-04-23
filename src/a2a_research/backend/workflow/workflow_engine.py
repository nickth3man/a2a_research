"""Claim-centric workflow engine.

Implements the full pipeline from flow.md:
  Preprocess → Clarify → Plan → Claim-centric loop →
  Synthesize → Critique → Postprocess
"""

from __future__ import annotations

import asyncio
from time import perf_counter

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.models import BudgetConsumption, ResearchSession
from a2a_research.backend.core.progress import Bus, ProgressQueue
from a2a_research.backend.core.settings import settings
from a2a_research.backend.workflow.definitions import (
    PER_STAGE_TIMEOUTS,
    STEP_INDEX,
    budget_from_settings,
    stage_timeout,
)
from a2a_research.backend.workflow.engine import drive
from a2a_research.backend.workflow.status import mark_running_failed

# Backward-compatible aliases for tests
_PER_STAGE_TIMEOUTS = PER_STAGE_TIMEOUTS
_budget_from_settings = budget_from_settings
_stage_timeout = stage_timeout

logger = get_logger(__name__)

__all__ = ["run_workflow_async", "run_workflow_sync"]


async def run_workflow_async(
    query: str, progress_queue: ProgressQueue | None = None
) -> ResearchSession:
    session = ResearchSession(query=query)
    session.roles = list(STEP_INDEX.keys())
    session.ensure_agent_results()
    started = perf_counter()
    logger.info("workflow start session_id=%s query=%r", session.id, query)

    import a2a_research.backend.core.a2a as _a2a

    client = _a2a.A2AClient(_a2a.get_registry())
    if progress_queue is not None:
        Bus.register(session.id, progress_queue)

    budget = budget_from_settings()
    session.budget_consumed = BudgetConsumption()

    try:
        try:
            await asyncio.wait_for(
                drive(session, client, query, budget),
                timeout=settings.workflow_timeout,
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
        return session
    finally:
        if progress_queue is not None:
            progress_queue.put_nowait(None)
            Bus.unregister(session.id)


def run_workflow_sync(query: str) -> ResearchSession:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        msg = (
            "run_workflow_sync cannot be called from a running event "
            "loop; use run_workflow_async instead."
        )
        raise RuntimeError(msg)
    return asyncio.run(run_workflow_async(query))
