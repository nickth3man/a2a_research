"""HTTP contract test for the Searcher service."""

from __future__ import annotations

import json

import httpx
import pytest
from a2a.types import Task

from a2a_research.a2a.client import extract_data_payloads
from a2a_research.agents.smolagents.searcher import main as searcher_main
from tests.http_harness import build_sdk_client, send_and_get_result


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_searcher_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        searcher_main,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "queries_used": ["jwst launch"],
                "hits": [
                    {
                        "url": "https://jwst.example",
                        "title": "JWST",
                        "snippet": "launch",
                        "source": "tavily",
                        "score": 0.9,
                    }
                ],
            }
        ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=searcher_main.build_http_app()),
        base_url="http://localhost:10002",
    ) as http_client:
        client = build_sdk_client(http_client, "http://localhost:10002")
        result = await send_and_get_result(
            client, payload={"queries": ["jwst launch"]}
        )

    assert isinstance(result, Task)
    assert (
        extract_data_payloads(result)[0]["hits"][0]["url"]
        == "https://jwst.example"
    )
