"""Exercise UI components with a stub Mesop component runtime."""

from __future__ import annotations

from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ResearchSession,
    Verdict,
)


def test_agent_timeline_card_renders_rows(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import agent_timeline_card

    session = ResearchSession(query="q")
    session.agent_results[AgentRole.RESEARCHER] = AgentResult(
        role=AgentRole.RESEARCHER,
        status=AgentStatus.COMPLETED,
        message="Retrieved 3 chunks",
    )
    agent_timeline_card(session)


def test_claims_panel_empty(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import claims_panel

    claims_panel(ResearchSession(query="q"))


def test_claims_panel_with_claim(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import claims_panel

    session = ResearchSession(query="q")
    session.agent_results[AgentRole.VERIFIER] = AgentResult(
        role=AgentRole.VERIFIER,
        status=AgentStatus.COMPLETED,
        claims=[
            Claim(
                text="Atomic",
                verdict=Verdict.SUPPORTED,
                confidence=0.9,
                sources=["doc_a"],
                evidence_snippets=["Supporting quote."],
            )
        ],
    )
    claims_panel(session)


def test_sources_panel_empty_and_with_citations(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import sources_panel

    sources_panel(ResearchSession(query="q"))
    session = ResearchSession(query="q")
    session.agent_results[AgentRole.RESEARCHER] = AgentResult(
        role=AgentRole.RESEARCHER,
        status=AgentStatus.COMPLETED,
        citations=["rag_accuracy"],
    )
    sources_panel(session)


def test_report_panel_empty_and_markdown(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import report_panel

    report_panel(ResearchSession(query="q"))
    report_panel(ResearchSession(query="q", final_report="# Title"))


def test_error_banner_truncates(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import error_banner

    error_banner("x" * 500)


def test_error_banner_short_message_no_ellipsis(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui import components as comp_mod

    assert comp_mod._error_banner_message("short") == "Pipeline error: short"
    assert not comp_mod._error_banner_message("short").endswith("…")


def test_loading_card_renders(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import loading_card

    loading_card(ResearchSession(query="q"))


def test_query_input_card(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import query_input_card

    def on_submit() -> None:
        return None

    def on_input() -> None:
        return None

    query_input_card(
        on_submit=on_submit,
        on_query_input=on_input,
    )
