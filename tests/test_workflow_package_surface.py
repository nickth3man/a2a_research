"""Coverage for workflow package helpers (get_graph, create_pocketflow_workflow)."""

from __future__ import annotations

from a2a_research.agents.pocketflow import create_pocketflow_workflow, get_graph
from a2a_research.models import AgentRole


def test_create_pocketflow_workflow_default_roles_seeds_shared_state() -> None:
    """Default factory must pre-seed a session and a messages list the nodes rely on."""
    adapter, shared = create_pocketflow_workflow()
    assert callable(adapter.invoke)
    assert callable(adapter.ainvoke)
    assert "session" in shared
    assert "messages" in shared
    assert shared["messages"] == []


def test_create_pocketflow_workflow_subset_roles_keeps_adapter_signature() -> None:
    """A subset roles graph must still expose the same callable adapter surface so
    ``run_workflow_from_session`` can plug a session into ``shared`` and invoke it."""
    roles = [AgentRole.RESEARCHER, AgentRole.ANALYST]
    adapter, shared = create_pocketflow_workflow(roles)
    assert callable(adapter.invoke)
    assert "session" in shared
    assert "messages" in shared
    assert "current_agent" in shared


def test_get_graph_returns_adapter_with_invoke_and_ainvoke() -> None:
    adapter = get_graph()
    assert callable(adapter.invoke)
    assert callable(adapter.ainvoke)
