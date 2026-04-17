"""Reader executor tests — mock fetch_many, assert Artifact shape."""

from __future__ import annotations

import pytest

from a2a_research.a2a import A2AClient, AgentRegistry, extract_data_payloads
from a2a_research.agents.smolagents.reader import ReaderExecutor
from a2a_research.agents.smolagents.reader import main as reader_main
from a2a_research.models import AgentRole
from a2a_research.tools.fetch import PageContent


@pytest.mark.asyncio
async def test_reader_fans_out_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[list[str]] = []

    async def fake_fetch_many(urls: list[str], max_chars: int = 8000) -> list[PageContent]:
        captured.append(urls)
        return [PageContent(url=u, title=u, markdown=f"# {u}", word_count=1) for u in urls]

    monkeypatch.setattr(reader_main, "fetch_many", fake_fetch_many)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.READER, payload={"urls": ["https://a.example", "https://b.example"]}
    )
    pages = extract_data_payloads(task)[0]["pages"]
    assert [p["url"] for p in pages] == ["https://a.example", "https://b.example"]
    assert captured == [["https://a.example", "https://b.example"]]


@pytest.mark.asyncio
async def test_reader_empty_urls(monkeypatch: pytest.MonkeyPatch) -> None:
    async def no_op(urls: list[str], max_chars: int = 8000) -> list[PageContent]:
        raise AssertionError("should not be called when urls is empty")

    monkeypatch.setattr(reader_main, "fetch_many", no_op)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(AgentRole.READER, payload={"urls": []})
    assert extract_data_payloads(task)[0]["pages"] == []


@pytest.mark.asyncio
async def test_reader_propagates_errors_in_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    async def partial(urls: list[str], max_chars: int = 8000) -> list[PageContent]:
        return [
            PageContent(url="https://ok.example", title="ok", markdown="# ok", word_count=1),
            PageContent(url="https://bad.example", error="fetch failed: boom"),
        ]

    monkeypatch.setattr(reader_main, "fetch_many", partial)

    registry = AgentRegistry()
    registry.register_factory(AgentRole.READER, ReaderExecutor)
    client = A2AClient(registry)

    task = await client.send(
        AgentRole.READER, payload={"urls": ["https://ok.example", "https://bad.example"]}
    )
    pages = extract_data_payloads(task)[0]["pages"]
    assert pages[1]["error"] == "fetch failed: boom"
    assert pages[0]["markdown"].startswith("# ok")
