"""Workflow entrypoints — run_workflow_async / run_workflow_sync."""

from __future__ import annotations

import asyncio
from typing import Any

from ..models import AgentRole, ResearchSession
from .builder import get_workflow
from .coordinator import run_coordinator


async def run_workflow(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    session = ResearchSession(query=query)

    flow, shared = get_workflow() if roles is None else get_workflow_for_roles(roles)
    shared["session"] = session

    await flow.run_async(shared)

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
