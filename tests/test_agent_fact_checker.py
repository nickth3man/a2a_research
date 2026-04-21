"""FactChecker tests — mock LLM to drive verification deterministically."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from a2a_research.agents.langgraph.fact_checker import run_fact_check
from a2a_research.agents.langgraph.fact_checker import (
    verify_route as fc_verify,
)
from a2a_research.models import Claim, Verdict
from a2a_research.tools import PageContent


def _fake_llm(payload: dict[str, Any]) -> Any:
    import json

    model = MagicMock()
    model.ainvoke = AsyncMock(
        return_value=MagicMock(content=json.dumps(payload))
    )
    return model


@pytest.mark.asyncio
async def test_fact_checker_verifies_with_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    evidence = [
        PageContent(
            url="https://a.example",
            title="A",
            markdown="# A\n\nEvidence.",
            word_count=2,
        )
    ]
    monkeypatch.setattr(
        fc_verify,
        "get_llm",
        lambda: _fake_llm(
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": "claim A",
                        "verdict": "SUPPORTED",
                        "confidence": 0.9,
                        "sources": ["https://a.example"],
                    }
                ],
                "follow_up_queries": [],
            }
        ),
    )

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A")],
        evidence=evidence,
        sources=[],
    )

    assert result["rounds"] == 1
    assert not result["search_exhausted"]
    assert result["verified_claims"][0].verdict == Verdict.SUPPORTED


@pytest.mark.asyncio
async def test_fact_checker_short_circuits_without_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No evidence provided → verify short-circuits, LLM is NEVER invoked."""

    llm_calls = {"count": 0}

    def _tripwire() -> Any:
        llm_calls["count"] += 1
        raise AssertionError(
            "verify must NOT call the LLM when no evidence is available"
        )

    monkeypatch.setattr(fc_verify, "get_llm", _tripwire)

    result = await run_fact_check(
        query="q",
        claims=[
            Claim(id="c0", text="claim A"),
            Claim(id="c1", text="claim B"),
        ],
        evidence=[],
        sources=[],
    )

    assert llm_calls["count"] == 0
    assert result["search_exhausted"] is True
    for claim in result["verified_claims"]:
        assert claim.verdict == Verdict.INSUFFICIENT_EVIDENCE
        assert claim.confidence == 0.0


@pytest.mark.asyncio
async def test_fact_checker_preserves_sources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from a2a_research.models import WebSource

    evidence = [
        PageContent(
            url="https://a.example",
            title="A",
            markdown="# A\n\nEvidence.",
            word_count=2,
        )
    ]
    sources = [
        WebSource(url="https://a.example", title="A", excerpt="Evidence.")
    ]
    monkeypatch.setattr(
        fc_verify,
        "get_llm",
        lambda: _fake_llm(
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": "claim A",
                        "verdict": "REFUTED",
                        "confidence": 0.8,
                    }
                ],
                "follow_up_queries": [],
            }
        ),
    )

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A")],
        evidence=evidence,
        sources=sources,
    )

    assert len(result["sources"]) == 1
    assert result["sources"][0].url == "https://a.example"
    assert result["verified_claims"][0].verdict == Verdict.REFUTED
