"""Tests for UI session helpers and ResearchSession JSON round-trips."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import AgentResult, AgentRole, AgentStatus, ResearchSession
from a2a_research.ui.session_state import has_results


class TestHasResults:
    def test_empty_agent_results(self) -> None:
        s = ResearchSession(query="q")
        assert has_results(s) is False

    def test_final_report_shortcut_without_terminal_statuses(self) -> None:
        s = ResearchSession(
            query="q",
            agent_results={
                AgentRole.RESEARCHER: AgentResult(
                    role=AgentRole.RESEARCHER,
                    status=AgentStatus.RUNNING,
                ),
            },
            final_report="# Done",
        )
        assert has_results(s) is True

    def test_all_completed(self) -> None:
        s = ResearchSession(
            query="q",
            agent_results={
                AgentRole.RESEARCHER: AgentResult(
                    role=AgentRole.RESEARCHER,
                    status=AgentStatus.COMPLETED,
                ),
                AgentRole.ANALYST: AgentResult(
                    role=AgentRole.ANALYST,
                    status=AgentStatus.COMPLETED,
                ),
            },
        )
        assert has_results(s) is True

    def test_all_failed_counts_as_terminal(self) -> None:
        s = ResearchSession(
            query="q",
            agent_results={
                AgentRole.RESEARCHER: AgentResult(
                    role=AgentRole.RESEARCHER,
                    status=AgentStatus.FAILED,
                ),
            },
        )
        assert has_results(s) is True

    def test_running_blocks_until_terminal(self) -> None:
        s = ResearchSession(
            query="q",
            agent_results={
                AgentRole.RESEARCHER: AgentResult(
                    role=AgentRole.RESEARCHER,
                    status=AgentStatus.COMPLETED,
                ),
                AgentRole.ANALYST: AgentResult(
                    role=AgentRole.ANALYST,
                    status=AgentStatus.RUNNING,
                ),
            },
        )
        assert has_results(s) is False


class TestResearchSessionJsonRoundTrip:
    def test_model_dump_json_validate_restores_session(self) -> None:
        original = ResearchSession(
            query="What is RAG?",
            agent_results={
                AgentRole.VERIFIER: AgentResult(
                    role=AgentRole.VERIFIER,
                    status=AgentStatus.COMPLETED,
                    message="ok",
                ),
            },
            final_report="## Report",
        )
        dumped = original.model_dump(mode="json")
        restored = ResearchSession.model_validate(dumped)
        assert restored.query == original.query
        assert restored.final_report == original.final_report
        assert restored.agent_results[AgentRole.VERIFIER].status == AgentStatus.COMPLETED

    def test_model_validate_rejects_bad_shape(self) -> None:
        with pytest.raises(ValidationError):
            ResearchSession.model_validate({"query": 123})
