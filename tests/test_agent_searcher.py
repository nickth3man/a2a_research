"""Searcher executor tests — assert smolagents path and artifact shape."""

from __future__ import annotations

import json
from typing import cast

import pytest
from a2a.types import Task, TaskState

from a2a_research.a2a import A2AClient, AgentRegistry, extract_data_payloads
from a2a_research.agents.smolagents.searcher import SearcherExecutor
from a2a_research.agents.smolagents.searcher import core as searcher_core
from a2a_research.agents.smolagents.searcher import main as searcher_main
from a2a_research.agents.smolagents.searcher.main import SearcherBatchResult
from a2a_research.models import AgentRole


class _FakeSearcherAgent:
    def __init__(self, payload: dict[str, object], calls: list[str]) -> None:
        self._payload = payload
        self._calls = calls

    def run(self, prompt: str) -> str:
        self._calls.append(prompt)
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_searcher_uses_agent_for_queries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        searcher_core,
        "build_agent",
        lambda: _FakeSearcherAgent(
            {
                "queries_used": ["jwst launch", "mirror diameter"],
                "hits": [
                    {
                        "url": "https://jwst.example",
                        "title": "JWST",
                        "snippet": "launch",
                        "source": "tavily",
                        "score": 0.9,
                    },
                    {
                        "url": "https://mirror.example",
                        "title": "Mirror",
                        "snippet": "diameter",
                        "source": "duckduckgo",
                        "score": 0.8,
                    },
                ],
            },
            calls,
        ),
    )

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = cast(
        "Task",
        await client.send(
            AgentRole.SEARCHER,
            payload={"queries": ["jwst launch", "mirror diameter"]},
        ),
    )
    payloads = extract_data_payloads(task)
    assert payloads
    hits = payloads[0]["hits"]
    assert {hit["url"] for hit in hits} == {
        "https://jwst.example",
        "https://mirror.example",
    }
    assert task.status.state == TaskState.TASK_STATE_COMPLETED
    assert calls and "jwst launch" in calls[0]


@pytest.mark.asyncio
async def test_searcher_empty_queries_returns_empty_hits() -> None:
    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = cast(
        "Task", await client.send(AgentRole.SEARCHER, payload={"queries": []})
    )
    payloads = extract_data_payloads(task)
    assert payloads[0]["hits"] == []
    assert task.status.state == TaskState.TASK_STATE_COMPLETED


@pytest.mark.asyncio
async def test_searcher_fails_when_agent_returns_only_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        searcher_core,
        "build_agent",
        lambda: _FakeSearcherAgent(
            {
                "queries_used": ["q"],
                "hits": [],
                "errors": [
                    "Tavily disabled (TAVILY_API_KEY is blank in .env).",
                    "DuckDuckGo request failed: 429",
                ],
            },
            [],
        ),
    )

    registry = AgentRegistry()
    registry.register_factory(AgentRole.SEARCHER, SearcherExecutor)
    client = A2AClient(registry)

    task = cast(
        "Task",
        await client.send(AgentRole.SEARCHER, payload={"queries": ["q"]}),
    )
    assert task.status.state == TaskState.TASK_STATE_FAILED
    payload = extract_data_payloads(task)[0]
    assert payload["hits"] == []
    assert any("Tavily disabled" in err for err in payload["errors"])


@pytest.mark.asyncio
async def test_searcher_dedupes_hits_from_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        searcher_core,
        "build_agent",
        lambda: _FakeSearcherAgent(
            {
                "queries_used": ["a", "b"],
                "hits": [
                    {
                        "url": "https://same.example",
                        "title": "same",
                        "snippet": "same",
                        "source": "tavily",
                        "score": 0.9,
                    },
                    {
                        "url": "https://same.example",
                        "title": "same-dup",
                        "snippet": "dup",
                        "source": "duckduckgo",
                        "score": 0.5,
                    },
                ],
            },
            [],
        ),
    )

    batch = await searcher_main.search_queries(["a", "b"])
    assert isinstance(batch, SearcherBatchResult)
    assert len(batch.hits) == 1
    assert batch.hits[0].url == "https://same.example"
    assert batch.errors == []
    assert sorted(batch.providers_successful) == ["duckduckgo", "tavily"]
