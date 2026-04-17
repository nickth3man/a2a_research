"""FactChecker graph tests — mock LLM + A2AClient to drive the loop deterministically."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from a2a.types import Artifact, DataPart, Part, Task, TaskState, TaskStatus

from a2a_research.agents.langgraph.fact_checker import run_fact_check
from a2a_research.agents.langgraph.fact_checker import verify_route as fc_verify
from a2a_research.models import AgentRole, Claim, Verdict


def _task_with(data: dict[str, Any]) -> Task:
    return Task(
        id="t",
        context_id="c",
        status=TaskStatus(state=TaskState.completed),
        artifacts=[
            Artifact(
                artifact_id="a",
                name="a",
                parts=[Part(root=DataPart(data=data))],
            )
        ],
    )


class FakeClient:
    """Routes Searcher/Reader requests to prepared payloads."""

    def __init__(
        self,
        search_responses: list[dict[str, Any]],
        read_responses: list[dict[str, Any]],
    ) -> None:
        self.search_responses = list(search_responses)
        self.read_responses = list(read_responses)
        self.search_calls = 0
        self.read_calls = 0

    async def send(
        self, role: AgentRole, payload: dict[str, Any] | None = None, **kw: Any
    ) -> Task:
        if role == AgentRole.SEARCHER:
            data = self.search_responses[min(self.search_calls, len(self.search_responses) - 1)]
            self.search_calls += 1
            return _task_with(data)
        if role == AgentRole.READER:
            data = self.read_responses[min(self.read_calls, len(self.read_responses) - 1)]
            self.read_calls += 1
            return _task_with(data)
        raise AssertionError(f"Unexpected role {role}")


def _fake_llm(payload: dict[str, Any]) -> Any:
    import json

    model = MagicMock()
    model.invoke.return_value = MagicMock(content=json.dumps(payload))
    return model


@pytest.mark.asyncio
async def test_fact_checker_converges_in_first_round(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(
        search_responses=[
            {
                "hits": [
                    {"url": "https://a.example", "title": "A", "snippet": "x", "source": "tavily"}
                ],
                "errors": [],
                "providers_successful": ["tavily", "duckduckgo"],
            }
        ],
        read_responses=[
            {
                "pages": [
                    {
                        "url": "https://a.example",
                        "title": "A",
                        "markdown": "# A\n\nEvidence.",
                        "word_count": 2,
                    }
                ]
            }
        ],
    )
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
        seed_queries=["q"],
        client=client,  # type: ignore[arg-type]
        max_rounds=3,
    )

    assert result["rounds"] == 1
    assert client.search_calls == 1
    assert client.read_calls == 1
    assert result["verified_claims"][0].verdict == Verdict.SUPPORTED


@pytest.mark.asyncio
async def test_fact_checker_loops_on_needs_more(monkeypatch: pytest.MonkeyPatch) -> None:
    client = FakeClient(
        search_responses=[
            {
                "hits": [
                    {"url": "https://a.example", "title": "A", "snippet": "x", "source": "tavily"}
                ],
                "errors": [],
                "providers_successful": ["tavily", "duckduckgo"],
            },
            {
                "hits": [
                    {"url": "https://b.example", "title": "B", "snippet": "y", "source": "ddg"}
                ],
                "errors": [],
                "providers_successful": ["tavily", "duckduckgo"],
            },
        ],
        read_responses=[
            {
                "pages": [
                    {"url": "https://a.example", "title": "A", "markdown": "# A", "word_count": 1}
                ]
            },
            {
                "pages": [
                    {"url": "https://b.example", "title": "B", "markdown": "# B", "word_count": 1}
                ]
            },
        ],
    )

    # First verify: NEEDS_MORE + follow-ups. Second verify: SUPPORTED, no follow-ups.
    responses = iter(
        [
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": "claim A",
                        "verdict": "NEEDS_MORE_EVIDENCE",
                        "confidence": 0.2,
                    }
                ],
                "follow_up_queries": ["better query"],
            },
            {
                "verified_claims": [
                    {"id": "c0", "text": "claim A", "verdict": "SUPPORTED", "confidence": 0.8}
                ],
                "follow_up_queries": [],
            },
        ]
    )

    def _model_factory() -> Any:
        return _fake_llm(next(responses))

    monkeypatch.setattr(fc_verify, "get_llm", _model_factory)

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A")],
        seed_queries=["initial"],
        client=client,  # type: ignore[arg-type]
        max_rounds=3,
    )

    assert result["rounds"] == 2
    assert client.search_calls == 2
    assert client.read_calls == 2
    assert result["verified_claims"][0].verdict == Verdict.SUPPORTED


@pytest.mark.asyncio
async def test_fact_checker_respects_max_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    # Providers RAN successfully (empty results are a valid outcome, not a failure),
    # so the loop should continue until max_rounds. But we still produce a single
    # page of evidence so the verify_node exercises the LLM path rather than the
    # no-evidence short-circuit.
    client = FakeClient(
        search_responses=[
            {
                "hits": [
                    {"url": "https://x.example", "title": "X", "snippet": "", "source": "tavily"}
                ],
                "errors": [],
                "providers_successful": ["tavily", "duckduckgo"],
            }
        ],
        read_responses=[
            {
                "pages": [
                    {
                        "url": "https://x.example",
                        "title": "X",
                        "markdown": "# X\n\nSomething.",
                        "word_count": 2,
                    }
                ]
            }
        ],
    )
    # LLM never converges — always NEEDS_MORE + follow-ups.
    monkeypatch.setattr(
        fc_verify,
        "get_llm",
        lambda: _fake_llm(
            {
                "verified_claims": [
                    {
                        "id": "c0",
                        "text": "claim A",
                        "verdict": "NEEDS_MORE_EVIDENCE",
                        "confidence": 0.1,
                    }
                ],
                "follow_up_queries": ["still trying"],
            }
        ),
    )

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A")],
        seed_queries=["q"],
        client=client,  # type: ignore[arg-type]
        max_rounds=2,
    )

    assert result["rounds"] == 2
    assert result["verified_claims"][0].verdict == Verdict.NEEDS_MORE_EVIDENCE


@pytest.mark.asyncio
async def test_fact_checker_marks_exhausted_and_sets_insufficient_when_all_providers_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """All providers failed → verify_node short-circuits, loop terminates after one pass,
    claims are INSUFFICIENT_EVIDENCE, the exact provider errors appear in the snippets,
    and the LLM is NEVER invoked (we don't want hallucinated verdicts)."""

    client = FakeClient(
        search_responses=[
            {
                "hits": [],
                "errors": [
                    "Tavily disabled (TAVILY_API_KEY is blank in .env).",
                    "DuckDuckGo request failed: 429",
                ],
                "providers_successful": [],
            }
        ],
        read_responses=[{"pages": []}],
    )

    llm_calls = {"count": 0}

    def _tripwire() -> Any:
        llm_calls["count"] += 1
        raise AssertionError("verify_node must NOT call the LLM when no evidence is available")

    monkeypatch.setattr(fc_verify, "get_llm", _tripwire)

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A"), Claim(id="c1", text="claim B")],
        seed_queries=["q"],
        client=client,  # type: ignore[arg-type]
        max_rounds=3,
    )

    assert llm_calls["count"] == 0
    assert result["search_exhausted"] is True
    assert any("Tavily disabled" in e for e in result["errors"])
    assert any("DuckDuckGo" in e for e in result["errors"])
    for claim in result["verified_claims"]:
        assert claim.verdict == Verdict.INSUFFICIENT_EVIDENCE
        assert claim.confidence == 0.0
        joined = " ".join(claim.evidence_snippets)
        assert "Tavily disabled" in joined
        assert "DuckDuckGo" in joined


@pytest.mark.asyncio
async def test_fact_checker_marks_exhausted_when_all_urls_fail_to_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Search returned hits but Reader could not extract any of them."""

    client = FakeClient(
        search_responses=[
            {
                "hits": [
                    {"url": "https://a.example", "title": "A", "snippet": "x", "source": "tavily"}
                ],
                "errors": [],
                "providers_successful": ["tavily"],
            }
        ],
        read_responses=[
            {
                "pages": [
                    {"url": "https://a.example", "error": "fetch failed: 403"},
                ]
            }
        ],
    )

    def _tripwire() -> Any:
        raise AssertionError("LLM must not be called on evidence-empty path")

    monkeypatch.setattr(fc_verify, "get_llm", _tripwire)

    result = await run_fact_check(
        query="q",
        claims=[Claim(id="c0", text="claim A")],
        seed_queries=["q"],
        client=client,  # type: ignore[arg-type]
        max_rounds=3,
    )

    assert any("Reader" in e and "fetch failed" in e for e in result["errors"])
    for claim in result["verified_claims"]:
        assert claim.verdict == Verdict.INSUFFICIENT_EVIDENCE
        assert any("fetch failed" in s for s in claim.evidence_snippets)
