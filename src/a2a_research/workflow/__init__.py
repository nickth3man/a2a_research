"""PocketFlow-backed async runtime for the 4-agent research pipeline."""

from __future__ import annotations

from typing import Any

from pocketflow_reference.pocketflow_source import AsyncFlow, AsyncNode

from ..models import AgentRole, ResearchSession
from .adapter import SyncWorkflowAdapter
from .builder import get_workflow
from .coordinator import run_coordinator
from .entrypoints import run_workflow_sync
from .nodes import ActorNode, create_actor_node
from .policy import PipelineOrderPolicy, PolicyEffect, WorkflowPolicy


__all__ = [
    "ActorNode",
    "AsyncFlow",
    "AsyncNode",
    "PipelineOrderPolicy",
    "PolicyEffect",
    "SyncWorkflowAdapter",
    "WorkflowPolicy",
    "create_actor_node",
    "create_pocketflow_workflow",
    "get_graph",
    "get_workflow",
    "run_coordinator",
    "run_research_sync",
    "run_workflow",
    "run_workflow_async",
    "run_workflow_sync",
]


def create_pocketflow_workflow(
    roles: list[AgentRole] | None = None,
):
    if roles is None:
        roles = [
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.VERIFIER,
            AgentRole.PRESENTER,
        ]

    flow, shared = get_workflow()
    return SyncWorkflowAdapter(flow, shared), shared


async def run_workflow(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    session = ResearchSession(query=query)
    adapter, shared = create_pocketflow_workflow(roles)
    shared["session"] = session
    await adapter.run_async(shared)
    return shared["session"]


async def run_workflow_async(
    query: str,
    roles: list[AgentRole] | None = None,
) -> ResearchSession:
    return await run_workflow(query, roles)


def run_research_sync(query: str) -> ResearchSession:
    import asyncio

    return asyncio.run(run_workflow(query))


async def run_coordinator_async(session: ResearchSession) -> ResearchSession:
    return await run_coordinator(session)


def get_graph():
    adapter, _ = create_pocketflow_workflow()
    return adapter
