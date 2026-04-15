"""LangGraph workflow — backward-compatible re-export for the PocketFlow runtime.

Public API (preserved from before):
    from a2a_research.graph import get_graph, run_research_sync

Both calls now route through the new PocketFlow workflow layer.
The underlying LangGraph implementation is preserved in _langgraph_impl
for callers that specifically need it.
"""

from __future__ import annotations

from ..workflow import (
    create_pocketflow_workflow,
    get_workflow,
    run_research_sync,
    run_workflow_async,
)
from ..models import (
    A2AMessage,
    AgentRole,
    ResearchSession,
    WorkflowState,
)

__all__ = [
    "A2AMessage",
    "AgentRole",
    "create_pocketflow_workflow",
    "get_graph",
    "get_workflow",
    "ResearchSession",
    "run_research_sync",
    "run_workflow_async",
    "WorkflowState",
]


def get_graph():
    adapter, _ = create_pocketflow_workflow()
    return adapter
