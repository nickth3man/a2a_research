"""End-to-end workflow test with every LLM + network call mocked."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from a2a_research.agents.langgraph.fact_checker import verify_route as fc_verify
from a2a_research.agents.pocketflow.planner import nodes as planner_nodes
from a2a_research.agents.pydantic_ai.synthesizer import agent as synth_agent
from a2a_research.agents.smolagents.reader import main as reader_main
from a2a_research.agents.smolagents.searcher import main as searcher_main
from a2a_research.models import AgentRole, AgentStatus, ReportOutput
from a2a_research.progress import ProgressEvent, ProgressPhase, drain_progress_while_running
from a2a_research.workflow import run_research_async


def _llm_stub(payload: dict[str, Any]) -> Any:
    model = MagicMock()
    model.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(payload)))
    return model


class _FakePydAgent:
    def __init__(self, report: ReportOutput) -> None:
        self._report = report

    async def run(self, prompt: str) -> Any:
        from types import SimpleNamespace

        return SimpleNamespace(output=self._report)


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


def _configure_success_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        planner_nodes,
        "get_llm",
        lambda: _llm_stub(
            {
                "claims": [{"id": "c0", "text": "JWST launched in December 2021."}],
                "seed_queries": ["JWST launch date"],
            }
        ),
    )

    monkeypatch.setattr(
        searcher_main,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["JWST launch date"],
                "hits": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "snippet": "launched 2021",
                        "source": "tavily",
                        "score": 0.9,
                    }
                ],
            }
        ),
    )

    monkeypatch.setattr(
        reader_main,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "pages": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "markdown": "# NASA\n\nJWST launched December 25, 2021.",
                        "word_count": 6,
                    }
                ]
            }
        ),
    )

    monkeypatch.setattr(
        fc_verify,
        "get_llm",
        lambda: _llm_stub(
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": "JWST launched in December 2021.",
                        "verdict": "SUPPORTED",
                        "confidence": 0.95,
                        "sources": ["https://nasa.example/jwst"],
                    }
                ],
                "follow_up_queries": [],
            }
        ),
    )

    synth_agent.reset_agent_cache()
    monkeypatch.setattr(
        synth_agent,
        "build_agent",
        lambda: _FakePydAgent(
            ReportOutput(
                title="JWST Launch",
                summary="JWST launched in December 2021.",
                sections=[],
            )
        ),
    )


@pytest.mark.asyncio
async def test_full_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_success_path(monkeypatch)

    session = await run_research_async("When did JWST launch?")

    assert session.error is None
    assert session.report is not None
    assert session.report.title == "JWST Launch"
    assert "JWST" in session.final_report
    assert len(session.sources) == 1
    assert session.sources[0].url == "https://nasa.example/jwst"
    statuses = {r: ar.status for r, ar in session.agent_results.items()}
    assert all(s == AgentStatus.COMPLETED for s in statuses.values())


@pytest.mark.asyncio
async def test_progress_events_emitted(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_success_path(monkeypatch)

    queue: asyncio.Queue[ProgressEvent | None] = asyncio.Queue()
    workflow_task = asyncio.create_task(
        run_research_async("When did JWST launch?", progress_queue=queue)
    )
    events = [event async for event in drain_progress_while_running(queue, workflow_task)]
    session = await workflow_task

    assert session.error is None
    started_roles = {event.role for event in events if event.phase == ProgressPhase.STEP_STARTED}
    assert started_roles == {
        AgentRole.PLANNER,
        AgentRole.SEARCHER,
        AgentRole.READER,
        AgentRole.FACT_CHECKER,
        AgentRole.SYNTHESIZER,
    }
    assert any(
        event.substep_label.startswith("round_") and event.phase == ProgressPhase.STEP_SUBSTEP
        for event in events
    )


@pytest.mark.asyncio
async def test_pipeline_aborts_when_search_providers_all_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When every search provider fails, the FactChecker must mark claims
    INSUFFICIENT_EVIDENCE, the Synthesizer must be skipped, and session.error
    must name the underlying providers so the user can debug."""

    from a2a_research.models import AgentRole, Verdict

    monkeypatch.setattr(
        planner_nodes,
        "get_llm",
        lambda: _llm_stub(
            {
                "claims": [{"id": "c0", "text": "JWST launched in December 2021."}],
                "seed_queries": ["JWST launch"],
            }
        ),
    )

    monkeypatch.setattr(
        searcher_main,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["JWST launch"],
                "hits": [],
                "errors": [
                    "Tavily disabled (TAVILY_API_KEY is blank in .env).",
                    "DuckDuckGo request failed: 429",
                ],
            }
        ),
    )

    def _reader_tripwire() -> object:
        raise AssertionError("Reader must not be invoked when Searcher produced no URLs")

    monkeypatch.setattr(reader_main, "build_agent", _reader_tripwire)

    # Tripwires on the FactChecker and Synthesizer LLMs — they must not run.
    def _fc_tripwire() -> Any:
        raise AssertionError("FactChecker LLM must not run when no evidence is available")

    monkeypatch.setattr(fc_verify, "get_llm", _fc_tripwire)

    synth_agent.reset_agent_cache()

    def _synth_tripwire() -> Any:
        raise AssertionError("Synthesizer must not run when FactChecker failed")

    monkeypatch.setattr(synth_agent, "build_agent", _synth_tripwire)

    session = await run_research_async("When did JWST launch?")

    assert session.error is not None
    assert "Tavily disabled" in session.error
    assert "DuckDuckGo" in session.error
    assert session.report is None  # Synthesizer was skipped
    # Claims marked INSUFFICIENT_EVIDENCE with the reason in the evidence_snippets.
    assert all(c.verdict == Verdict.INSUFFICIENT_EVIDENCE for c in session.claims)
    joined = " ".join(s for c in session.claims for s in c.evidence_snippets)
    assert "Tavily disabled" in joined
    # Agent statuses reflect the failure explicitly.
    statuses = {r: ar.status for r, ar in session.agent_results.items()}
    assert statuses[AgentRole.PLANNER] == AgentStatus.COMPLETED
    assert statuses[AgentRole.SEARCHER] == AgentStatus.FAILED
    assert statuses[AgentRole.FACT_CHECKER] == AgentStatus.FAILED
    assert statuses[AgentRole.SYNTHESIZER] == AgentStatus.FAILED
    # final_report explains the failure in human terms.
    assert "Research unavailable" in session.final_report
    assert "Tavily disabled" in session.final_report
