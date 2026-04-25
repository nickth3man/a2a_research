"""Tests for workflow.status helpers not covered by integration tests."""

from __future__ import annotations

from core import AgentResult, AgentRole, AgentStatus, ResearchSession
from workflow.status import mark_running_failed


def test_mark_running_failed_sets_failed_for_running_results() -> None:
    s = ResearchSession(
        query="q",
        agent_results={
            AgentRole.PLANNER: AgentResult(
                role=AgentRole.PLANNER,
                status=AgentStatus.RUNNING,
            )
        },
    )
    mark_running_failed(s)
    r = s.agent_results[AgentRole.PLANNER]
    assert r.status == AgentStatus.FAILED
    assert "Aborted" in r.message
