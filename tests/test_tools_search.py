"""Tests for parallel Tavily + Brave + DuckDuckGo web search with explicit
errors.
"""

from __future__ import annotations

import pytest

from a2a_research.tools import search as search_module
from a2a_research.tools.search import SearchResult, WebHit, web_search

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


@pytest.mark.asyncio
async def test_web_search_records_ddg_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def ok_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://t.example",
                    title="t",
                    source="tavily",
                    score=0.5,
                )
            ],
            None,
        )

    async def ok_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], None)

    def raising_ddg_sync(query: str, max_results: int) -> list[WebHit]:
        raise RuntimeError("ddg http 429")

    monkeypatch.setattr(search_module, "_search_tavily", ok_tavily)
    monkeypatch.setattr(search_module, "_search_brave", ok_brave)
    import a2a_research.tools.search_ddg as ddg_module

    monkeypatch.setattr(ddg_module, "_search_ddg_sync", raising_ddg_sync)

    result = await web_search("any")
    urls = [h.url for h in result.hits]
    assert urls == ["https://t.example"]
    assert any("DuckDuckGo request failed" in err for err in result.errors)
    assert result.providers_successful == ["tavily", "brave"]


@pytest.mark.asyncio
async def test_web_search_adds_diagnostic_when_zero_hits_and_no_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def empty_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], None

    async def empty_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], None

    async def empty_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], None

    monkeypatch.setattr(search_module, "_search_tavily", empty_tavily)
    monkeypatch.setattr(search_module, "_search_brave", empty_brave)
    monkeypatch.setattr(search_module, "_search_ddg", empty_ddg)

    result = await web_search("anything")
    assert result.hits == []
    assert len(result.errors) == 1
    assert "zero hits" in result.errors[0].lower()
    assert set(result.providers_successful) == {
        "tavily",
        "brave",
        "duckduckgo",
    }


@pytest.mark.asyncio
async def test_web_search_reports_all_three_providers_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "Tavily request failed: network down"

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "Brave request failed: HTTP 401"

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "DuckDuckGo request failed: 429"

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("any")
    assert result.hits == []
    assert len(result.errors) == 3
    assert result.providers_successful == []
    assert result.any_provider_succeeded is False
