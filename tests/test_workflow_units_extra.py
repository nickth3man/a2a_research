"""Unit tests for workflow adapter, coordinator, policy, and ActorNode branches."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from a2a_research.agents.pocketflow.adapter import SyncWorkflowAdapter
from a2a_research.agents.pocketflow.nodes import ActorNode
from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ResearchSession,
    Verdict,
    WorkflowState,
)


@pytest.mark.asyncio
async def test_sync_workflow_adapter_run_async() -> None:
    flow = MagicMock()
    flow.run_async = AsyncMock()
    adapter = SyncWorkflowAdapter(flow, {"messages": []})
    shared: dict = {"session": ResearchSession(query="q")}
    await adapter.run_async(shared)
    flow.run_async.assert_awaited_once_with(shared)


@pytest.mark.asyncio
async def test_sync_workflow_adapter_ainvoke() -> None:
    flow = MagicMock()
    flow.run_async = AsyncMock()
    adapter = SyncWorkflowAdapter(flow, {"messages": [], "current_agent": None})
    session = ResearchSession(query="q")
    state = WorkflowState(session=session)
    out = await adapter.ainvoke(state)
    assert out["session"] is session
    flow.run_async.assert_awaited_once()


def test_sync_workflow_adapter_invoke() -> None:
    flow = MagicMock()
    flow.run_async = AsyncMock()
    adapter = SyncWorkflowAdapter(flow, {"messages": [], "current_agent": None})
    session = ResearchSession(query="q")
    state = WorkflowState(session=session)
    out = adapter.invoke(state)
    flow.run_async.assert_awaited_once()
    assert out["session"] is session


@pytest.mark.asyncio
async def test_run_coordinator_runs_flow() -> None:
    flow = MagicMock()
    flow.run_async = AsyncMock()
    with patch(
        "a2a_research.agents.pocketflow.coordinator.build_coordinator",
        return_value=flow,
    ):
        from a2a_research.agents.pocketflow.coordinator import run_coordinator

        session = ResearchSession(query="coord")
        out = await run_coordinator(session)
    assert out is session
    flow.run_async.assert_awaited_once()


def test_build_coordinator_returns_flow() -> None:
    from a2a_research.agents.pocketflow.coordinator import build_coordinator

    flow = build_coordinator()
    assert flow is not None


def test_pipeline_order_policy_validate_transition() -> None:
    from a2a_research.agents.pocketflow.policy import PipelineOrderPolicy

    policy = PipelineOrderPolicy(name="pipeline_order")
    assert policy.validate_transition(None, AgentRole.RESEARCHER.value) is True


@pytest.mark.asyncio
async def test_actor_prep_async_requires_session() -> None:
    node = ActorNode(AgentRole.RESEARCHER)
    with pytest.raises(ValueError, match="session"):
        await node.prep_async({})


@pytest.mark.asyncio
async def test_actor_exec_async_missing_handler() -> None:
    node = ActorNode(AgentRole.RESEARCHER)
    session = ResearchSession(query="q")
    with patch(
        "a2a_research.a2a.server.A2AClient.send",
        return_value=AgentResult(
            role=AgentRole.RESEARCHER,
            status=AgentStatus.FAILED,
            message="No handler registered for researcher",
        ),
    ):
        result = await node.exec_async({"session": session, "shared": {}})
    assert result.status == AgentStatus.FAILED
    assert "handler" in result.message.lower()


@pytest.mark.asyncio
async def test_actor_exec_async_handler_raises() -> None:
    def boom(_message: object, _session: ResearchSession) -> AgentResult:
        raise RuntimeError("agent boom")

    node = ActorNode(AgentRole.RESEARCHER)
    session = ResearchSession(query="q")
    with (
        patch("a2a_research.a2a.server.A2AClient.send", side_effect=boom),
        pytest.raises(RuntimeError, match="agent boom"),
    ):
        await node.exec_async({"session": session, "shared": {}})


@pytest.mark.asyncio
async def test_actor_post_async_presenter_sets_final_report() -> None:
    node = ActorNode(AgentRole.PRESENTER)
    session = ResearchSession(query="q")
    prep = {"session": session}
    exec_res = AgentResult(
        role=AgentRole.PRESENTER,
        status=AgentStatus.COMPLETED,
        raw_content="# Final",
    )
    shared: dict = {"session": session, "messages": [], "current_agent": None}
    out = await node.post_async(shared, prep, exec_res)
    assert out == "default"
    assert session.final_report == "# Final"


def test_adapter_get_graph_factory() -> None:
    with patch(
        "a2a_research.agents.pocketflow.adapter.get_workflow",
        return_value=(MagicMock(), {}),
    ):
        from a2a_research.agents.pocketflow.adapter import get_graph as adapter_get_graph

        adapter = adapter_get_graph()
    assert isinstance(adapter, SyncWorkflowAdapter)


def test_actor_build_payload_unknown_role_returns_empty() -> None:
    from a2a_research.agents.pocketflow.actor_helpers import build_payload

    _ = ActorNode(role=cast("AgentRole", "nonstandard_role"))
    payload = build_payload(cast("Any", "nonstandard_role"), ResearchSession(query="q"))
    assert payload == {}


@pytest.mark.asyncio
async def test_actor_build_payload_branches() -> None:
    """Exercise _build_payload for analyst, verifier, presenter via exec_async."""
    session = ResearchSession(query="Q")
    session.agent_results[AgentRole.RESEARCHER] = AgentResult(
        role=AgentRole.RESEARCHER,
        status=AgentStatus.COMPLETED,
        raw_content="summary",
        citations=["c1"],
    )
    session.agent_results[AgentRole.ANALYST] = AgentResult(
        role=AgentRole.ANALYST,
        status=AgentStatus.COMPLETED,
        claims=[Claim(text="c", verdict=Verdict.SUPPORTED)],
    )
    session.agent_results[AgentRole.VERIFIER] = AgentResult(
        role=AgentRole.VERIFIER,
        status=AgentStatus.COMPLETED,
        claims=[Claim(text="v", verdict=Verdict.SUPPORTED)],
    )

    def handler(_m: object, _s: ResearchSession) -> AgentResult:
        return AgentResult(role=AgentRole.ANALYST, status=AgentStatus.COMPLETED)

    for role in (
        AgentRole.RESEARCHER,
        AgentRole.ANALYST,
        AgentRole.VERIFIER,
        AgentRole.PRESENTER,
    ):
        node = ActorNode(role)
        with patch("a2a_research.a2a.server.A2AClient.send", side_effect=handler):
            await node.exec_async({"session": session, "shared": {}})
