from __future__ import annotations

from unittest.mock import patch

from a2a_research.models import (
    AgentRole,
    Claim,
    ResearchSession,
    Verdict,
    WebSource,
    workflow_v2_roles,
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
        session.sources = [
            WebSource(url="https://doc1.example", title="D1"),
            WebSource(url="https://doc2.example", title="D2"),
            WebSource(url="https://doc1.example", title="dup"),
            WebSource(url="https://doc3.example", title="D3"),
        ]
        assert get_all_citations(session) == [
            "https://doc1.example",
            "https://doc2.example",
            "https://doc3.example",
        ]

    def test_empty_sources_returns_empty(self) -> None:
        session = ResearchSession(query="q")
        assert get_all_citations(session) == []


class TestGetVerifiedClaims:
    def test_returns_session_claims(self) -> None:
        session = ResearchSession(query="q")
        session.claims = [Claim(text="claim1", verdict=Verdict.SUPPORTED)]
        claims = get_verified_claims(session)
        assert len(claims) == 1
        assert claims[0].text == "claim1"

    def test_empty_returns_empty(self) -> None:
        session = ResearchSession(query="q")
        assert get_verified_claims(session) == []


class TestGetAgentLabel:
    def test_known_role(self) -> None:
        assert get_agent_label(AgentRole.PLANNER) == "Planner"
        assert get_agent_label(AgentRole.FACT_CHECKER) == "FactChecker"

    def test_fallback_to_role_value(self) -> None:
        with patch.dict(
            "a2a_research.ui.data_access.AGENT_CARDS", {}, clear=True
        ):
            assert get_agent_label(AgentRole.SEARCHER) == "searcher"


class TestGetAllRoles:
    def test_uses_session_roles(self) -> None:
        session = ResearchSession(query="q", roles=[AgentRole.SEARCHER])
        assert get_all_roles(session) == [AgentRole.SEARCHER]

    def test_fallback_when_session_none(self) -> None:
        assert get_all_roles(None) == workflow_v2_roles()

    def test_fallback_when_session_empty_roles(self) -> None:
        session = ResearchSession(query="q", roles=[])
        assert get_all_roles(session) == workflow_v2_roles()


class TestFormatSourceDisplay:
    def test_formats_url_host_and_tail(self) -> None:
        assert (
            format_source_display("https://nasa.example/jwst")
            == "nasa.example/jwst"
        )

    def test_host_only_when_root(self) -> None:
        assert format_source_display("https://example.com/") == "example.com"

    def test_falls_back_to_title_case_for_non_urls(self) -> None:
        assert format_source_display("rag_accuracy") == "Rag Accuracy"
