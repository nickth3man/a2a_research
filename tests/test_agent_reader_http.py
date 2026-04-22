"""HTTP contract test for the Reader service."""

from __future__ import annotations

import json

import httpx
import pytest
from a2a.types import Task

from a2a_research.a2a.client import extract_data_payloads
from a2a_research.agents.smolagents.reader import core as reader_core
from a2a_research.agents.smolagents.reader import main as reader_main
from tests.http_harness import build_sdk_client, send_and_get_result


class _FakeJSONAgent:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def run(self, prompt: str) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_reader_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        reader_core,
        "build_agent",
        lambda: _FakeJSONAgent(
            {
                "pages": [
                    {
                        "url": "https://a.example",
                        "title": "A",
                        "markdown": "# A",
                        "word_count": 1,
                    }
                ]
            }
        ),
    )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=reader_main.build_http_app()),
        base_url="http://localhost:10003",
    ) as http_client:
        client = await build_sdk_client(http_client, "http://localhost:10003")
        result = await send_and_get_result(
            client, payload={"urls": ["https://a.example"]}
        )

    assert isinstance(result, Task)
    assert (
        extract_data_payloads(result)[0]["pages"][0]["url"]
        == "https://a.example"
    )
