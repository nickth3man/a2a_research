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
    from a2a_research.ui.components import CardTimeline

    session = ResearchSession(query="q")
    session.agent_results[AgentRole.PLANNER] = AgentResult(
        role=AgentRole.PLANNER,
        status=AgentStatus.COMPLETED,
        message="Retrieved 3 chunks",
    )
    CardTimeline(session)


def test_claims_panel_empty(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import PanelClaims

    PanelClaims(ResearchSession(query="q"))


def test_claims_panel_with_claim(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import PanelClaims

    session = ResearchSession(query="q")
    session.agent_results[AgentRole.FACT_CHECKER] = AgentResult(
        role=AgentRole.FACT_CHECKER,
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
    PanelClaims(session)


def test_sources_panel_empty_and_with_citations(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import PanelSources

    PanelSources(ResearchSession(query="q"))
    session = ResearchSession(query="q")
    session.agent_results[AgentRole.PLANNER] = AgentResult(
        role=AgentRole.PLANNER,
        status=AgentStatus.COMPLETED,
        citations=["rag_accuracy"],
    )
    PanelSources(session)


def test_report_panel_empty_and_markdown(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import PanelReport

    PanelReport(ResearchSession(query="q"))
    PanelReport(ResearchSession(query="q", final_report="# Title"))


def test_error_banner_truncates(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import BannerError

    BannerError("x" * 500)


def test_error_banner_short_message_no_ellipsis(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components.banners import _error_banner_message

    assert _error_banner_message("short") == "Pipeline error: short"
    assert not _error_banner_message("short").endswith("\u2026")


def test_loading_card_renders(stub_mesop_component_runtime: None) -> None:
    from a2a_research.models import ResearchSession
    from a2a_research.ui.components import CardLoading

    CardLoading(
        progress_step_label="Step 2 of 4",
        session=ResearchSession(query="Q"),
        running_substeps=["Calling LLM…"],
        activity_by_role={},
    )


def test_report_panel_renders_without_html_iframe(stub_mesop_component_runtime: None) -> None:
    from unittest.mock import patch

    from a2a_research.ui.components import PanelReport

    with patch("a2a_research.ui.components.report.me.html") as html_mock:
        PanelReport(ResearchSession(query="q", final_report="# Title"))

    html_mock.assert_not_called()


def test_query_input_card(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import CardQueryInput

    def on_submit(_event: object) -> None:
        return None

    def on_input(_event: object) -> None:
        return None

    CardQueryInput(
        on_submit=on_submit,
        on_query_input=on_input,
    )
