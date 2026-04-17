"""Searcher executor tests — mock web_search, assert Artifact shape."""

from __future__ import annotations

import pytest
from a2a.types import TaskState

from a2a_research.a2a import A2AClient, AgentRegistry, extract_data_payloads
from a2a_research.agents.smolagents.searcher import SearcherExecutor
from a2a_research.agents.smolagents.searcher import main as searcher_main
from a2a_research.models import AgentRole
from a2a_research.tools.search import SearchResult, WebHit


def _result(
    hits: list[WebHit], errors: list[str] | None = None, successful: list[str] | None = None
) -> SearchResult:
    return SearchResult(
        hits=hits,
        errors=errors or [],
        providers_attempted=["tavily", "duckduckgo"],
        providers_successful=successful if successful is not None else ["tavily", "duckduckgo"],
    )


@pytest.mark.asyncio
async def test_searcher_fans_out_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    async def fake_search(query: str, max_results: int | None = None) -> SearchResult:
        calls.append(query)
        return _result(
            [WebHit(url=f"https://{query}.example", title=query, source="tavily", score=0.5)]
        )

    monkeypatch.setattr(searcher_main, "web_search", fake_search)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.SEARCHER, payload={"queries": ["jwst launch", "mirror diameter"]}
    )
    payloads = extract_data_payloads(task)
    assert payloads, "expected a DataArtifact"
    hits = payloads[0]["hits"]
    assert {h["url"] for h in hits} == {
        "https://jwst launch.example",
        "https://mirror diameter.example",
    }
    assert sorted(calls) == ["jwst launch", "mirror diameter"]
    assert task.status.state == TaskState.completed
    assert payloads[0]["errors"] == []


@pytest.mark.asyncio
async def test_searcher_empty_queries_returns_empty_hits() -> None:
    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.SEARCHER, payload={"queries": []})
    payloads = extract_data_payloads(task)
    assert payloads[0]["hits"] == []
    assert task.status.state == TaskState.completed


@pytest.mark.asyncio
async def test_searcher_dedupes_across_queries(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_search(query: str, max_results: int | None = None) -> SearchResult:
        return _result(
            [
                WebHit(url="https://same.example", title="same", source="tavily", score=0.9),
                WebHit(url=f"https://{query}.example", title=query, source="tavily", score=0.5),
            ]
        )

    monkeypatch.setattr(searcher_main, "web_search", fake_search)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.SEARCHER, payload={"queries": ["a", "b"]})
    hits = extract_data_payloads(task)[0]["hits"]
    assert len([h for h in hits if h["url"] == "https://same.example"]) == 1


@pytest.mark.asyncio
async def test_searcher_fails_when_every_provider_errored(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def broken_search(query: str, max_results: int | None = None) -> SearchResult:
        return _result(
            hits=[],
            errors=[
                "Tavily disabled (TAVILY_API_KEY is blank in .env).",
                "DuckDuckGo request failed: 429",
            ],
            successful=[],
        )

    monkeypatch.setattr(searcher_main, "web_search", broken_search)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.SEARCHER, payload={"queries": ["q"]})
    assert task.status.state == TaskState.failed
    payload = extract_data_payloads(task)[0]
    assert payload["hits"] == []
    assert any("Tavily disabled" in err for err in payload["errors"])
    assert any("DuckDuckGo" in err for err in payload["errors"])
    assert payload["providers_successful"] == []


@pytest.mark.asyncio
async def test_searcher_still_completes_when_one_provider_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def partial_search(query: str, max_results: int | None = None) -> SearchResult:
        return _result(
            hits=[WebHit(url="https://ok.example", title="ok", source="duckduckgo")],
            errors=["Tavily disabled (TAVILY_API_KEY is blank in .env)."],
            successful=["duckduckgo"],
        )

    monkeypatch.setattr(searcher_main, "web_search", partial_search)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.SEARCHER, payload={"queries": ["q"]})
    assert task.status.state == TaskState.completed
    payload = extract_data_payloads(task)[0]
    assert any("Tavily disabled" in err for err in payload["errors"])
    assert payload["providers_successful"] == ["duckduckgo"]
    assert len(payload["hits"]) == 1
