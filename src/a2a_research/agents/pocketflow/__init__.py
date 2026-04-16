"""PocketFlow-backed async runtime for the 4-agent research pipeline.

Importing this package triggers per-agent registration in
:mod:`a2a_research.agents.pocketflow.utils.registry`, then exposes the composed
``AsyncFlow``, actor nodes, policy hooks, and convenience callers:

- ``run_research_sync(query)`` — blocking entry for scripts, tests, and REPL use.
- ``run_workflow_async`` / ``run_workflow`` — async orchestration with logging.
- ``get_workflow`` / ``get_graph`` — access the built graph or a sync adapter.

The shared dict must map the key ``session`` to a :class:`~a2a_research.models.ResearchSession`.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from a2a_research.models.policy import PolicyEffect, WorkflowPolicy

if TYPE_CHECKING:
    from a2a_research.models import AgentRole, ResearchSession

# Importing each subpackage triggers `register_agent(...)` on the shared registry.
from . import analyst as _analyst  # noqa: F401
from . import presenter as _presenter  # noqa: F401
from . import researcher as _researcher  # noqa: F401
from . import verifier as _verifier  # noqa: F401
from .analyst import analyst_invoke, parse_claims_from_analyst
from .entrypoints import (
    get_workflow_for_roles,
    run_workflow,
    run_workflow_async,
    run_workflow_sync,
)
from .flow import get_workflow
from .presenter import presenter_invoke
from .researcher import researcher_invoke
from .utils.adapter import SyncWorkflowAdapter
from .utils.coordinator import build_coordinator, run_coordinator
from .utils.nodes import ActorNode, create_actor_node
from .utils.policy import PipelineOrderPolicy
from .utils.registry import (
    AgentRegistry,
    AgentSpec,
    get_agent_handler,
    get_agent_spec,
    get_registry,
    register_agent,
)
from .verifier import parse_verified_claims, verifier_invoke

__all__ = [
    "ActorNode",
    "AgentRegistry",
    "AgentSpec",
    "PipelineOrderPolicy",
    "PolicyEffect",
    "SyncWorkflowAdapter",
    "WorkflowPolicy",
    "analyst_invoke",
    "build_coordinator",
    "create_actor_node",
    "create_pocketflow_workflow",
    "get_agent_handler",
    "get_agent_spec",
    "get_graph",
    "get_registry",
    "get_workflow",
    "parse_claims_from_analyst",
    "parse_verified_claims",
    "presenter_invoke",
    "register_agent",
    "researcher_invoke",
    "run_coordinator",
    "run_research_sync",
    "run_workflow",
    "run_workflow_async",
    "run_workflow_sync",
    "verifier_invoke",
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
