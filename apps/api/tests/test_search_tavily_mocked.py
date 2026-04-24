"""Mocked Tavily search tests — core happy-path behavior."""

from __future__ import annotations

import pytest

from a2a_research.backend.tools import search as search_module
from a2a_research.backend.tools.search import WebHit, web_search


def _make_hit(
    url: str = "https://example.com",
    title: str = "Example",
    snippet: str = "A snippet.",
    source: str = "tavily",
    score: float = 0.9,
) -> WebHit:
    return WebHit(
        url=url, title=title, snippet=snippet, source=source, score=score
    )


async def _empty_provider(q: str, n: int) -> tuple[list[WebHit], str | None]:
    return [], None


@pytest.mark.asyncio
async def test_tavily_search_returns_hits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [_make_hit()], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    result = await web_search("test query")
    assert len(result.hits) >= 1
    assert result.hits[0].source == "tavily"


@pytest.mark.asyncio
async def test_tavily_hit_structure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            WebHit(
                url="https://structured.example",
                title="Structured Hit",
                snippet="Detailed snippet text",
                source="tavily",
                score=0.85,
            )
        ], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    hit = (await web_search("structure check")).hits[0]
    assert hit.url == "https://structured.example"
    assert hit.title == "Structured Hit"
    assert hit.snippet == "Detailed snippet text"
    assert hit.source == "tavily"
    assert hit.score == 0.85


@pytest.mark.asyncio
async def test_tavily_max_results_respected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        hits = [_make_hit(url=f"https://h{i}.example") for i in range(5)]
        return hits[:n], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    result = await web_search("truncation", max_results=3)
    assert len(result.hits) <= 3


@pytest.mark.asyncio
async def test_tavily_score_positive(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            _make_hit(url="https://s1.example", score=0.1),
            _make_hit(url="https://s2.example", score=0.99),
        ], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    for hit in (await web_search("scores")).hits:
        assert hit.score > 0


@pytest.mark.asyncio
async def test_tavily_unicode_query(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_queries: list[str] = []

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured_queries.append(q)
        return [_make_hit()], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    result = await web_search("München Germany history")
    assert len(result.hits) >= 1
    assert captured_queries[0] == "München Germany history"


@pytest.mark.asyncio
async def test_tavily_popular_query(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        hits = [
            _make_hit(url=f"https://pop{i}.example", score=0.9 - i * 0.1)
            for i in range(5)
        ]
        return hits, None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)
    result = await web_search("popular query", max_results=10)
    assert len(result.hits) >= 5
