from __future__ import annotations

from unittest.mock import patch

from a2a_research.models import (
    AgentResult,
    AgentRole,
    Claim,
    ResearchSession,
    Verdict,
    default_roles,
)
from a2a_research.ui.data_access import (
    get_agent_label,
    get_all_citations,
    get_all_roles,
    get_verified_claims,
)
from a2a_research.ui.formatting import format_source_display


class TestGetAllCitations:
    def test_dedupes_preserves_order(self) -> None:
        session = ResearchSession(query="q")
        session.agent_results[AgentRole.RESEARCHER] = AgentResult(
            role=AgentRole.RESEARCHER,
            citations=["doc1", "doc2", "doc1"],
        )
        session.agent_results[AgentRole.VERIFIER] = AgentResult(
            role=AgentRole.VERIFIER,
            citations=["doc2", "doc3"],
        )
        assert get_all_citations(session) == ["doc1", "doc2", "doc3"]

    def test_empty_agents_returns_empty(self) -> None:
        session = ResearchSession(query="q")
        assert get_all_citations(session) == []


class TestGetVerifiedClaims:
    def test_returns_verifier_claims(self) -> None:
        session = ResearchSession(query="q")
        session.agent_results[AgentRole.VERIFIER] = AgentResult(
            role=AgentRole.VERIFIER,
            claims=[Claim(text="claim1", verdict=Verdict.SUPPORTED)],
        )
        claims = get_verified_claims(session)
        assert len(claims) == 1
        assert claims[0].text == "claim1"

    def test_empty_returns_empty(self) -> None:
        session = ResearchSession(query="q")
        assert get_verified_claims(session) == []


class TestGetAgentLabel:
    def test_known_role(self) -> None:
        assert get_agent_label(AgentRole.RESEARCHER) == "Researcher"

    def test_fallback_to_role_value(self) -> None:
        with patch.dict("a2a_research.ui.data_access.AGENT_CARDS", {}, clear=True):
            assert get_agent_label(AgentRole.ANALYST) == "analyst"


class TestGetAllRoles:
    def test_uses_session_roles(self) -> None:
        session = ResearchSession(query="q", roles=[AgentRole.ANALYST])
        assert get_all_roles(session) == [AgentRole.ANALYST]

    def test_fallback_when_session_none(self) -> None:
        assert get_all_roles(None) == default_roles()

    def test_fallback_when_session_empty_roles(self) -> None:
        session = ResearchSession(query="q", roles=[])
        assert get_all_roles(session) == default_roles()


class TestFormatSourceDisplay:
    def test_normalizes_underscores_and_hyphens(self) -> None:
        assert format_source_display("arxiv_paper-2024") == "Arxiv Paper 2024"

    def test_simple_string(self) -> None:
        assert format_source_display("rag_accuracy") == "Rag Accuracy"
