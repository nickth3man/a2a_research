"""Public workflow runners and graph selection.

- ``run_workflow`` / ``run_workflow_async`` — execute the flow for a query; populate the ``session`` key in the shared dict.
- ``run_workflow_sync`` — asyncio runner for contexts without a running loop.
- ``get_workflow_for_roles`` — optional subset or reordering of :class:`~a2a_research.models.AgentRole`.

Logging records session id, timing, and failures around ``AsyncFlow.run_async``.
"""

from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any

from ..app_logging import get_logger
from ..models import AgentRole, ResearchSession
from .builder import get_workflow
from .coordinator import run_coordinator

logger = get_logger(__name__)


async def run_workflow(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    session = ResearchSession(query=query)
    logger.info(
        "Workflow start session_id=%s query=%r roles=%s",
        session.id,
        query,
        [role.value for role in roles] if roles else "default",
    )
    started_at = perf_counter()

    flow, shared = get_workflow() if roles is None else get_workflow_for_roles(roles)
    shared["session"] = session

    try:
        await flow.run_async(shared)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception("Workflow failed session_id=%s elapsed_ms=%.1f", session.id, elapsed_ms)
        raise

    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Workflow completed session_id=%s elapsed_ms=%.1f agents=%s final_report_chars=%s",
        session.id,
        elapsed_ms,
        [role.value for role in shared["session"].agent_results],
        len(shared["session"].final_report),
    )

    return shared["session"]


def run_workflow_sync(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    return asyncio.run(run_workflow(query, roles))


async def run_workflow_async(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    return await run_workflow(query, roles)


async def run_workflow_from_session(
    session: ResearchSession,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    return await run_coordinator(session)


def get_workflow_for_roles(roles: list[AgentRole]) -> tuple[Any, dict[str, Any]]:
    from .builder import build_workflow

    return build_workflow(roles)
