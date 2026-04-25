"""Tests for web search merge and deduplication behavior."""

from __future__ import annotations

import pytest

from tools import SearchResult, WebHit, web_search
from tools import search as search_module

_SNIPPET_SEP = search_module._SNIPPET_MERGE_SEP


@pytest.mark.asyncio
async def test_web_search_merges_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://a.example",
                    title="T:a",
                    snippet="t",
                    source="tavily",
                    score=0.9,
                )
            ],
            None,
        )

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://c.example",
                    title="B:c",
                    snippet="b",
                    source="brave",
                    score=0.95,
                )
            ],
            None,
        )

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://b.example",
                    title="D:b",
                    snippet="d",
                    source="duckduckgo",
                ),
                WebHit(
                    url="https://a.example",
                    title="D:a",
                    snippet="d",
                    source="duckduckgo",
                ),
            ],
            None,
        )

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("any query", max_results=5)
    assert isinstance(result, SearchResult)
    urls = [h.url for h in result.hits]
    assert {
        "https://a.example",
        "https://b.example",
        "https://c.example",
    } <= set(urls)
    a_hit = next(h for h in result.hits if h.url == "https://a.example")
    assert a_hit.source == "duckduckgo,tavily"
    assert a_hit.snippet == f"t{_SNIPPET_SEP}d"
    assert result.errors == []
    assert set(result.providers_successful) == {
        "tavily",
        "brave",
        "duckduckgo",
    }


@pytest.mark.asyncio
async def test_web_search_merge_same_url_tavily_and_brave_snippets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://x.example",
                    title="T",
                    snippet="alpha",
                    source="tavily",
                    score=0.5,
                )
            ],
            None,
        )

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://x.example",
                    title="B",
                    snippet="beta",
                    source="brave",
                    score=0.99,
                )
            ],
            None,
        )

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("q", max_results=5)
    assert len(result.hits) == 1
    h = result.hits[0]
    assert "alpha" in h.snippet and "beta" in h.snippet
    assert h.source == "brave,tavily"
