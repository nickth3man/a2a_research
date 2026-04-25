"""Reader executor tests — assert smolagents path and artifact shape."""

from __future__ import annotations

import json

import pytest

from agents.smolagents.reader import ReaderExecutor
from agents.smolagents.reader import core as reader_core
from core import AgentRole
from core.a2a import (
    A2AClient,
    AgentRegistry,
    extract_data_payloads,
)


class _FakeReaderAgent:
    def __init__(self, payload: dict[str, object], calls: list[str]) -> None:
        self._payload = payload
        self._calls = calls

    def run(self, prompt: str) -> str:
        self._calls.append(prompt)
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_reader_uses_agent_for_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    monkeypatch.setattr(
        reader_core,
        "build_agent",
        lambda: _FakeReaderAgent(
            {
                "pages": [
                    {
                        "url": "https://a.example",
                        "title": "A",
                        "markdown": "# A",
                        "word_count": 1,
                    },
                    {
                        "url": "https://b.example",
                        "title": "B",
                        "markdown": "# B",
                        "word_count": 1,
                    },
                ]
            },
            calls,
        ),
    )

    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.READER,
        payload={"urls": ["https://a.example", "https://b.example"]},
    )
    pages = extract_data_payloads(task)[0]["pages"]
    assert [page["url"] for page in pages] == [
        "https://a.example",
        "https://b.example",
    ]
    assert calls and "https://a.example" in calls[0]


@pytest.mark.asyncio
async def test_reader_empty_urls() -> None:
    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.READER, payload={"urls": []})
    assert extract_data_payloads(task)[0]["pages"] == []


@pytest.mark.asyncio
async def test_reader_propagates_errors_in_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reader_core,
        "build_agent",
        lambda: _FakeReaderAgent(
            {
                "pages": [
                    {
                        "url": "https://ok.example",
                        "title": "ok",
                        "markdown": "# ok",
                        "word_count": 1,
                    },
                    {
                        "url": "https://bad.example",
                        "error": "fetch failed: boom",
                    },
                ]
            },
            [],
        ),
    )

    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.READER,
        payload={"urls": ["https://ok.example", "https://bad.example"]},
    )
    pages = extract_data_payloads(task)[0]["pages"]
    assert pages[1]["error"] == "fetch failed: boom"
    assert pages[0]["markdown"].startswith("# ok")
