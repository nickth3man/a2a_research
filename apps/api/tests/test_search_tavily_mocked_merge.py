"""Mocked Tavily search tests — provider merge behavior."""

from __future__ import annotations

import pytest

from tools import WebHit, web_search
from tools import search as search_module


def make_hit(
    url: str,
    source: str,
    score: float,
) -> WebHit:
    return WebHit(
        url=url,
        title="Example",
        snippet="A snippet.",
        source=source,
        score=score,
    )


@pytest.mark.asyncio
async def test_web_search_merges_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            make_hit(url="https://tav.example", source="tavily", score=0.9)
        ], None

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            make_hit(url="https://brave.example", source="brave", score=0.8)
        ], None

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [
            make_hit(url="https://ddg.example", source="duckduckgo", score=0.7)
        ], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    urls = {
        hit.url
        for hit in (await web_search("merge test", max_results=10)).hits
    }
    assert "https://tav.example" in urls
    assert "https://brave.example" in urls
    assert "https://ddg.example" in urls


@pytest.mark.asyncio
async def test_web_search_deduplication(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dup_url = "https://dup.example"

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [make_hit(url=dup_url, source="tavily", score=0.9)], None

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [make_hit(url=dup_url, source="brave", score=0.8)], None

    async def fake_ddg(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [make_hit(url=dup_url, source="duckduckgo", score=0.7)], None

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)
    monkeypatch.setattr(search_module, "_search_ddg", fake_ddg)

    urls = [
        hit.url
        for hit in (await web_search("dedup test", max_results=10)).hits
    ]
    assert urls.count(dup_url) == 1
