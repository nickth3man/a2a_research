"""Claim-centric workflow engine (v2).

Implements the full pipeline from workflow.md:
  Preprocess → Clarify → Plan → Claim-centric loop →
  Synthesize → Critique → Postprocess

The claim-centric loop traverses claims in DAG topological order,
gathering evidence iteratively until all claims are resolved,
budget is exhausted, or novelty drops.
"""

from __future__ import annotations

import asyncio
from time import perf_counter

from a2a_research.logging.app_logging import get_logger
from a2a_research.models import BudgetConsumption, ResearchSession
from a2a_research.progress import Bus, ProgressQueue
from a2a_research.settings import settings
from a2a_research.workflow.definitions import (
    PER_STAGE_TIMEOUTS,
    budget_from_settings,
    stage_timeout,
)
from a2a_research.workflow.engine import drive_v2
from a2a_research.workflow.status import mark_running_failed

# Backward-compatible aliases for tests
_PER_STAGE_TIMEOUTS = PER_STAGE_TIMEOUTS
_budget_from_settings = budget_from_settings
_stage_timeout = stage_timeout


logger = get_logger(__name__)

__all__ = ["run_workflow_v2_async", "run_workflow_v2_sync"]


async def run_workflow_v2_async(
    query: str, progress_queue: ProgressQueue | None = None
) -> ResearchSession:
    session = ResearchSession(query=query)
    from a2a_research.workflow.definitions import STEP_INDEX_V2

    session.roles = list(STEP_INDEX_V2.keys())
    session.ensure_agent_results()
    started = perf_counter()
    logger.info("workflow_v2 start session_id=%s query=%r", session.id, query)

    from a2a_research.a2a import A2AClient, get_registry

    client = A2AClient(get_registry())
    if progress_queue is not None:
        Bus.register(session.id, progress_queue)

    budget = budget_from_settings()
    session.budget_consumed = BudgetConsumption()

    try:
        await asyncio.wait_for(
            drive_v2(session, client, query, budget),
            timeout=settings.workflow_timeout,
        )
    except TimeoutError:
        session.error = (
            f"Workflow timed out after {settings.workflow_timeout:.0f}s "
            "— partial results below."
        )
        mark_running_failed(session)
        logger.warning("workflow_v2 timed out session_id=%s", session.id)
    except Exception as exc:
        session.error = str(exc)
        mark_running_failed(session)
        logger.exception("workflow_v2 failed session_id=%s", session.id)

    elapsed_ms = (perf_counter() - started) * 1000
    logger.info(
        "workflow_v2 done session_id=%s elapsed_ms=%.1f error=%s",
        session.id,
        elapsed_ms,
        session.error,
    )
    if progress_queue is not None:
        progress_queue.put_nowait(None)
        Bus.unregister(session.id)
    return session


def run_workflow_v2_sync(query: str) -> ResearchSession:
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is not None:
        msg = (
            "run_workflow_v2_sync cannot be called from a running event "
            "loop; use run_workflow_v2_async instead."
        )
        raise RuntimeError(msg)
    return asyncio.run(run_workflow_v2_async(query))
