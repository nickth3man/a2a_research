"""HTTP contract test for the FactChecker service."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.types import Task

from a2a_research.a2a.client import extract_data_payloads
from a2a_research.a2a.registry import AgentRegistry
from a2a_research.agents.langgraph.fact_checker import main as fact_checker_main
from a2a_research.agents.langgraph.fact_checker import verify_route as fc_verify
from a2a_research.agents.smolagents.reader import main as reader_main
from a2a_research.agents.smolagents.searcher import main as searcher_main
from tests.http_harness import build_sdk_client, make_multi_app_client, send_and_get_result


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_fact_checker_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        searcher_main,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["JWST launch"],
                "hits": [
                    {
                        "url": "https://nasa.example/jwst",
                        "title": "NASA JWST",
                        "snippet": "launch",
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
    model = MagicMock()
    model.ainvoke = AsyncMock(
        return_value=MagicMock(
            content=json.dumps(
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
            )
        )
    )
    monkeypatch.setattr(fc_verify, "get_llm", lambda: model)

    apps = {
        "http://localhost:10002": searcher_main.build_http_app(),
        "http://localhost:10003": reader_main.build_http_app(),
        "http://localhost:10004": fact_checker_main.build_http_app(),
    }
    shared_client = make_multi_app_client(apps)

    from a2a_research.a2a import client as client_module

    def _client_factory(*args: object, **kwargs: object) -> Any:
        return shared_client

    monkeypatch.setattr(client_module.httpx, "AsyncClient", _client_factory)
    monkeypatch.setattr(
        client_module,
        "get_registry",
        lambda: AgentRegistry(
            searcher_url="http://localhost:10002",
            reader_url="http://localhost:10003",
            fact_checker_url="http://localhost:10004",
        ),
    )

    sdk_client = build_sdk_client(shared_client, "http://localhost:10004")
    result = await send_and_get_result(
        sdk_client,
        payload={
            "query": "When did JWST launch?",
            "claims": [{"id": "c0", "text": "JWST launched in December 2021."}],
            "seed_queries": ["JWST launch"],
        },
    )
    assert isinstance(result, Task)
    assert extract_data_payloads(result)[0]["verified_claims"][0]["id"] == "c0"
    await shared_client.aclose()
