"""Tests for parallel Tavily + DuckDuckGo web search with explicit errors."""

from __future__ import annotations

import pytest

from a2a_research.tools import search as search_module
from a2a_research.tools.search import SearchResult, WebHit, web_search


@pytest.mark.asyncio
async def test_web_search_merges_providers(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(
                    url="https://a.example", title="T:a", snippet="t", source="tavily", score=0.9
                )
            ],
            None,
        )

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return (
            [
                WebHit(url="https://b.example", title="D:b", snippet="d", source="duckduckgo"),
                WebHit(url="https://a.example", title="D:a", snippet="d", source="duckduckgo"),
            ],
            None,
        )

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("any query", max_results=5)
    assert isinstance(result, SearchResult)
    urls = [h.url for h in result.hits]
    assert {"https://a.example", "https://b.example"} <= set(urls)
    a_hit = next(h for h in result.hits if h.url == "https://a.example")
    assert a_hit.source == "tavily"
    assert result.errors == []
    assert set(result.providers_successful) == {"tavily", "duckduckgo"}


@pytest.mark.asyncio
async def test_web_search_records_tavily_blank_key_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([WebHit(url="https://only.example", title="only", source="duckduckgo")], None)

    monkeypatch.setattr(search_module.settings, "tavily_api_key", "")
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("any", max_results=3)
    assert [h.source for h in result.hits] == ["duckduckgo"]
    assert any("Tavily disabled" in err for err in result.errors)
    assert result.providers_successful == ["duckduckgo"]


@pytest.mark.asyncio
async def test_web_search_records_ddg_request_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def ok_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([WebHit(url="https://t.example", title="t", source="tavily", score=0.5)], None)

    def raising_ddg_sync(query: str, max_results: int) -> list[WebHit]:
        raise RuntimeError("ddg http 429")

    monkeypatch.setattr(search_module, "_search_tavily", ok_tavily)
    monkeypatch.setattr(search_module, "_search_ddg_sync", raising_ddg_sync)

    result = await web_search("any")
    urls = [h.url for h in result.hits]
    assert urls == ["https://t.example"]
    assert any("DuckDuckGo request failed" in err for err in result.errors)
    assert result.providers_successful == ["tavily"]


@pytest.mark.asyncio
async def test_web_search_reports_both_providers_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "Tavily request failed: network down"

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "DuckDuckGo request failed: 429"

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    result = await web_search("any")
    assert result.hits == []
    assert len(result.errors) == 2
    assert result.providers_successful == []
    assert result.any_provider_succeeded is False


@pytest.mark.asyncio
async def test_tavily_branch_skips_when_api_key_blank(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(search_module.settings, "tavily_api_key", "")
    hits, err = await search_module._search_tavily("q", 3)
    assert hits == []
    assert err is not None and "Tavily disabled" in err
