"""Mocked tests for Brave provider happy-path behavior."""

from __future__ import annotations

import pytest

from a2a_research.backend.tools import search as search_module
from a2a_research.backend.tools.search import WebHit, web_search


async def _empty_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
    return [], None


async def _empty_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
    return [], None


def _stub_other_providers(mp: pytest.MonkeyPatch) -> None:
    mp.setattr(search_module, "_search_tavily", _empty_tavily)
    mp.setattr(search_module, "_search_ddg", _empty_ddg)


@pytest.mark.asyncio
async def test_brave_search_returns_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            WebHit(
                url="https://example.com/1",
                title="Example 1",
                snippet="First result",
                source="brave",
                score=0.9,
            )
        ], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    result = await web_search("test query")
    assert len(result.hits) >= 1
    assert any(h.source == "brave" for h in result.hits)


@pytest.mark.asyncio
async def test_brave_hit_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            WebHit(
                url="https://example.com/struct",
                title="Structure Test",
                snippet="Checking all fields",
                source="brave",
                score=0.85,
            )
        ], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    result = await web_search("structure query")
    brave_hits = [h for h in result.hits if h.source == "brave"]
    assert len(brave_hits) == 1
    hit = brave_hits[0]
    assert hit.url == "https://example.com/struct"
    assert hit.title == "Structure Test"
    assert hit.snippet == "Checking all fields"
    assert hit.source == "brave"
    assert hit.score == 0.85


@pytest.mark.asyncio
async def test_brave_max_results_respected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        hits = [
            WebHit(
                url=f"https://example.com/{i}",
                title=f"Hit {i}",
                snippet=f"Snippet {i}",
                source="brave",
                score=0.9 - i * 0.1,
            )
            for i in range(5)
        ]
        return hits[:n], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    result = await web_search("max results query", max_results=3)
    assert len([h for h in result.hits if h.source == "brave"]) <= 3


@pytest.mark.asyncio
async def test_brave_results_have_distinct_urls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            WebHit(
                url="https://example.com/a",
                title="A",
                snippet="sa",
                source="brave",
                score=0.9,
            ),
            WebHit(
                url="https://example.com/b",
                title="B",
                snippet="sb",
                source="brave",
                score=0.8,
            ),
            WebHit(
                url="https://example.com/c",
                title="C",
                snippet="sc",
                source="brave",
                score=0.7,
            ),
        ], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    result = await web_search("distinct urls")
    urls = [h.url for h in result.hits if h.source == "brave"]
    assert len(urls) == len(set(urls))


@pytest.mark.asyncio
async def test_brave_query_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured["q"] = q
        return [
            WebHit(
                url="https://example.com/passthrough",
                title="Passthrough",
                snippet="s",
                source="brave",
                score=0.9,
            )
        ], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    await web_search("hello world 123")
    assert captured["q"] == "hello world 123"


@pytest.mark.asyncio
async def test_brave_unicode_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str] = {}

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured["q"] = q
        return [
            WebHit(
                url="https://example.com/münchen",
                title="München",
                snippet="Bavarian capital",
                source="brave",
                score=0.9,
            )
        ], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    result = await web_search("München Germany history")
    assert captured["q"] == "München Germany history"
    assert len(result.hits) >= 1
