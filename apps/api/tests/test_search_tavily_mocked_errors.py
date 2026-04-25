"""Mocked Tavily search tests — error and edge cases."""

from __future__ import annotations

import pytest

from tests.test_search_tavily_mocked import _empty_provider, _make_hit
from tools import WebHit, web_search
from tools import search as search_module


@pytest.mark.asyncio
async def test_tavily_error_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """API errors are surfaced in SearchResult.errors."""

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "API error")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("error test")
    assert any("API error" in e for e in result.errors)


@pytest.mark.asyncio
async def test_tavily_empty_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty results (no hits, no error) are handled gracefully."""

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("empty test")
    # No Tavily-specific error — just no hits from Tavily
    tavily_errors = [e for e in result.errors if "tavily" in e.lower()]
    assert tavily_errors == []


@pytest.mark.asyncio
async def test_tavily_timeout_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Timeout errors are surfaced in SearchResult.errors."""

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "Request timed out")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("timeout test")
    assert any("timed out" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_tavily_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON errors are surfaced in SearchResult.errors."""

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return ([], "Malformed JSON")

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    result = await web_search("malformed test")
    assert any("malformed" in e.lower() for e in result.errors)


@pytest.mark.asyncio
async def test_tavily_query_passthrough(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The query string is forwarded to the Tavily provider unchanged."""

    captured: list[str] = []

    async def fake_tavily(q: str, n: int) -> tuple[list[WebHit], str | None]:
        captured.append(q)
        return ([_make_hit()], None)

    monkeypatch.setattr(search_module, "_search_tavily", fake_tavily)
    monkeypatch.setattr(search_module, "_search_brave", _empty_provider)
    monkeypatch.setattr(search_module, "_search_ddg", _empty_provider)

    await web_search("exact query passthrough")
    assert captured == ["exact query passthrough"]
