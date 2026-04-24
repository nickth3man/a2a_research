"""Tests for trafilatura-backed page fetch + extract."""

from __future__ import annotations

from typing import Any

import pytest

from a2a_research.backend.tools import fetch as fetch_module
from a2a_research.backend.tools.fetch import (
    PageContent,
    fetch_and_extract,
    fetch_many,
)


@pytest.mark.asyncio
async def test_fetch_and_extract_happy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_sync(url: str, max_chars: int) -> PageContent:
        return PageContent(
            url=url,
            title="Example Page",
            markdown="# Example Page\n\nBody content here.",
            word_count=4,
        )

    monkeypatch.setattr(fetch_module, "_fetch_sync", fake_fetch_sync)
    page = await fetch_and_extract("https://x.example")
    assert page.url == "https://x.example"
    assert page.title == "Example Page"
    assert "Body content" in page.markdown
    assert page.error is None


@pytest.mark.asyncio
async def test_fetch_and_extract_propagates_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_sync(url: str, max_chars: int) -> PageContent:
        return PageContent(url=url, error="fetch failed: boom")

    monkeypatch.setattr(fetch_module, "_fetch_sync", fake_fetch_sync)
    page = await fetch_and_extract("https://bad.example")
    assert page.error == "fetch failed: boom"
    assert page.markdown == ""


@pytest.mark.asyncio
async def test_fetch_many_parallel(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_sync(url: str, max_chars: int) -> PageContent:
        return PageContent(
            url=url, title=url, markdown=f"content of {url}", word_count=3
        )

    monkeypatch.setattr(fetch_module, "_fetch_sync", fake_fetch_sync)
    pages = await fetch_many(["https://1.example", "https://2.example"])
    assert [p.url for p in pages] == ["https://1.example", "https://2.example"]


def test_fetch_sync_uses_trafilatura(monkeypatch: pytest.MonkeyPatch) -> None:
    import trafilatura as _traf

    called: dict[str, Any] = {}

    def fake_fetch_url(url: str) -> str:
        called["url"] = url
        return "<html><body><h1>T</h1><p>Body</p></body></html>"

    def fake_extract(downloaded: str, **kwargs: Any) -> str:
        called["kwargs"] = kwargs
        return "# T\n\nBody"

    monkeypatch.setattr(_traf, "fetch_url", fake_fetch_url)
    monkeypatch.setattr(_traf, "extract", fake_extract)
    page = fetch_module._fetch_sync("https://t.example", 8000)
    assert page.error is None
    assert page.title == "T"
    assert page.word_count > 0
    assert called["url"] == "https://t.example"
    assert called["kwargs"].get("output_format") == "markdown"


def test_fetch_sync_handles_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    import trafilatura as _traf

    monkeypatch.setattr(_traf, "fetch_url", lambda url: None)
    page = fetch_module._fetch_sync("https://empty.example", 8000)
    assert page.error and "empty" in page.error
