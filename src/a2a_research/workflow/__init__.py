"""PocketFlow-backed async runtime for the 4-agent research pipeline."""

from __future__ import annotations

import asyncio
from typing import Any

from pocketflow import AsyncFlow, AsyncNode

from ..models import AgentRole, ResearchSession  # noqa: TC001
from ..models.policy import PolicyEffect, WorkflowPolicy
from .adapter import SyncWorkflowAdapter
from .builder import get_workflow
from .coordinator import run_coordinator
from .entrypoints import (
    get_workflow_for_roles,
    run_workflow_sync,
)
from .entrypoints import (
    run_workflow as run_workflow,
)
from .entrypoints import (
    run_workflow_async as run_workflow_async,
)
from .nodes import ActorNode, create_actor_node
from .policy import PipelineOrderPolicy

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
) -> tuple[SyncWorkflowAdapter, dict[str, Any]]:
    flow, shared = get_workflow_for_roles(roles) if roles else get_workflow()
    return SyncWorkflowAdapter(flow, shared), shared


def run_research_sync(query: str) -> ResearchSession:
    return asyncio.run(run_workflow(query))


def get_graph() -> SyncWorkflowAdapter:
    adapter, _ = create_pocketflow_workflow()
    return adapter
