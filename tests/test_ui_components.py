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
    session.agent_results[AgentRole.RESEARCHER] = AgentResult(
        role=AgentRole.RESEARCHER,
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
    PanelClaims(session)


def test_sources_panel_empty_and_with_citations(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import PanelSources

    PanelSources(ResearchSession(query="q"))
    session = ResearchSession(query="q")
    session.agent_results[AgentRole.RESEARCHER] = AgentResult(
        role=AgentRole.RESEARCHER,
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
        progress_pct=0.4,
        progress_step_label="Step 2 of 4",
        progress_substep_label="Calling LLM…",
        session=ResearchSession(query="Q"),
        granularity=2,
        running_substeps=["Calling LLM…"],
    )


def test_query_input_card(stub_mesop_component_runtime: None) -> None:
    from a2a_research.ui.components import CardQueryInput

    def on_submit() -> None:
        return None

    def on_input() -> None:
        return None

    CardQueryInput(
        on_submit=on_submit,
        on_query_input=on_input,
    )
