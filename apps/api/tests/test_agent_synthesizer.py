"""Synthesizer executor smoke tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from a2a_research.backend.agents.pydantic_ai.synthesizer import (
    SynthesizerExecutor,
)
from a2a_research.backend.agents.pydantic_ai.synthesizer import (
    agent as synth_agent,
)
from a2a_research.backend.core.a2a import (
    A2AClient,
    AgentRegistry,
    extract_data_payloads,
    extract_text,
)
from a2a_research.backend.core.models import (
    AgentRole,
    Claim,
    ReportOutput,
    Verdict,
    WebSource,
)


@pytest.fixture(autouse=True)
def _reset_synth_cache() -> Any:
    synth_agent.reset_agent_cache()
    yield
    synth_agent.reset_agent_cache()


class _FakeAgent:
    def __init__(self, report: ReportOutput) -> None:
        self._report = report

    async def run(self, prompt: str) -> SimpleNamespace:
        return SimpleNamespace(output=self._report)


@pytest.mark.asyncio
async def test_synthesizer_emits_report_and_markdown_artifacts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = ReportOutput(title="T", summary="S", sections=[])
    monkeypatch.setattr(synth_agent, "build_agent", lambda: _FakeAgent(report))

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SYNTHESIZER, SynthesizerExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.SYNTHESIZER,
        payload={
            "query": "Why is the sky blue?",
            "verified_claims": [
                Claim(
                    id="c1",
                    text="Rayleigh scattering dominates daytime sky color.",
                    verdict=Verdict.SUPPORTED,
                    confidence=0.9,
                    sources=["https://x.example"],
                ).model_dump()
            ],
            "sources": [
                WebSource(url="https://x.example", title="X").model_dump(
                    mode="json"
                )
            ],
        },
    )

    payloads = extract_data_payloads(task)
    assert payloads, "expected a DataPart artifact"
    assert payloads[0]["report"]["title"] == "T"

    markdown = extract_text(task)
    assert "# T" in markdown and "S" in markdown


@pytest.mark.asyncio
async def test_synthesizer_failure_emits_stub_report(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Boom:
        async def run(self, prompt: str) -> Any:
            raise RuntimeError("llm down")

    monkeypatch.setattr(synth_agent, "build_agent", lambda: _Boom())

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SYNTHESIZER, SynthesizerExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.SYNTHESIZER,
        payload={"query": "q", "verified_claims": [], "sources": []},
    )
    payloads = extract_data_payloads(task)
    assert payloads[0]["report"]["title"] == "Report unavailable"
    assert "llm down" in payloads[0]["report"]["summary"]
