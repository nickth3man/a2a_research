"""Coverage for workflow package helpers (get_graph, create_pocketflow_workflow)."""

from __future__ import annotations

from a2a_research.models import AgentRole
from a2a_research.workflow import create_pocketflow_workflow, get_graph


def test_create_pocketflow_workflow_default_roles() -> None:
    adapter, shared = create_pocketflow_workflow()
    assert adapter is not None
    assert isinstance(shared, dict)


def test_create_pocketflow_workflow_subset_roles() -> None:
    roles = [AgentRole.RESEARCHER, AgentRole.ANALYST]
    adapter, shared = create_pocketflow_workflow(roles)
    assert adapter is not None
    assert isinstance(shared, dict)


def test_get_graph_returns_adapter() -> None:
    adapter = get_graph()
    assert adapter is not None
