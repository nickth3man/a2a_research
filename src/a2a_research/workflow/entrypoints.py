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
from ..models import AgentRole, AgentStatus, ResearchSession, default_roles
from ..progress import ProgressQueue, create_progress_reporter
from ..settings import settings
from .builder import get_workflow

logger = get_logger(__name__)


def _normalize_roles(roles: list[AgentRole] | None) -> list[AgentRole] | None:
    if roles is None:
        return None
    deduped: list[AgentRole] = []
    for role in roles:
        if role not in deduped:
            deduped.append(role)
    return deduped


async def run_workflow(
    query: str,
    roles: list[AgentRole] | None = None,
    progress_queue: ProgressQueue | None = None,
    granularity: int = 1,
) -> ResearchSession:
    normalized_roles = _normalize_roles(roles)
    session = ResearchSession(query=query, roles=normalized_roles or default_roles())
    session.ensure_agent_results()
    logger.info(
        "Workflow start session_id=%s query=%r roles=%s",
        session.id,
        query,
        [role.value for role in normalized_roles] if normalized_roles else "default",
    )
    started_at = perf_counter()

    try:
        return await run_workflow_from_session(
            session,
            normalized_roles,
            progress_queue=progress_queue,
            granularity=granularity,
        )
    except Exception as exc:
        elapsed_ms = (perf_counter() - started_at) * 1000
        session.error = str(exc)
        logger.exception("Workflow failed session_id=%s elapsed_ms=%.1f", session.id, elapsed_ms)
        raise


def run_workflow_sync(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    return asyncio.run(run_workflow(query, roles))


async def run_workflow_async(
    query: str,
    roles: list[AgentRole] | None = None,
    progress_queue: ProgressQueue | None = None,
    granularity: int = 1,
) -> ResearchSession:
    return await run_workflow(query, roles, progress_queue=progress_queue, granularity=granularity)


async def run_workflow_from_session(
    session: ResearchSession,
    roles: list[AgentRole] | None = None,
    progress_queue: ProgressQueue | None = None,
    granularity: int = 1,
) -> ResearchSession:
    explicit_roles = _normalize_roles(roles)
    normalized_roles = explicit_roles or _normalize_roles(session.roles) or default_roles()
    session.roles = normalized_roles
    session.ensure_agent_results()
    use_default_flow = explicit_roles is None and normalized_roles == default_roles()
    flow, shared = get_workflow() if use_default_flow else get_workflow_for_roles(normalized_roles)
    shared["session"] = session
    if progress_queue is not None:
        shared["progress_reporter"] = create_progress_reporter(
            asyncio.get_running_loop(), progress_queue
        )
        shared["progress_granularity"] = granularity
    try:
        await asyncio.wait_for(flow.run_async(shared), timeout=settings.workflow_timeout)
    except TimeoutError:
        timed_out_session: ResearchSession = shared["session"]
        timed_out_session.error = f"Workflow timed out after {settings.workflow_timeout:.1f}s. Partial results are shown below."
        for agent_result in timed_out_session.agent_results.values():
            if agent_result.status == AgentStatus.RUNNING:
                agent_result.status = AgentStatus.FAILED
                agent_result.message = "Timed out while running."
        logger.warning(
            "Workflow timed out session_id=%s timeout_s=%.1f",
            timed_out_session.id,
            settings.workflow_timeout,
        )
        return timed_out_session
    result: ResearchSession = shared["session"]
    logger.info(
        "Workflow completed session_id=%s agents=%s final_report_chars=%s error=%r",
        result.id,
        [role.value for role in result.agent_results],
        len(result.final_report),
        result.error,
    )
    return result


def get_workflow_for_roles(roles: list[AgentRole]) -> tuple[Any, dict[str, Any]]:
    from .builder import build_workflow

    normalized_roles = _normalize_roles(roles) or []
    return build_workflow(normalized_roles)
