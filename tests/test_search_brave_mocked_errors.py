"""Mocked tests for Brave search provider behaviour — error cases."""

from __future__ import annotations

import pytest

from a2a_research.backend.tools import search as search_module
from a2a_research.backend.tools.search import WebHit, web_search
from tests.test_search_brave_mocked import _stub_other_providers


@pytest.mark.asyncio
async def test_brave_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTTP 500 errors are surfaced in SearchResult.errors."""

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "HTTP 500 error"

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)

    result = await web_search("error query")
    assert any("HTTP 500" in e for e in result.errors)
    assert "brave" not in result.providers_successful


@pytest.mark.asyncio
async def test_brave_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty results (no hits, no error) are handled gracefully."""

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], None

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)

    result = await web_search("empty brave")
    # Brave contributed no hits but also no error — it counts as successful.
    assert "brave" in result.providers_successful


@pytest.mark.asyncio
async def test_brave_timeout_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout errors are surfaced in SearchResult.errors."""

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "Request timed out"

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)

    result = await web_search("timeout query")
    assert any("timed out" in e.lower() for e in result.errors)
    assert "brave" not in result.providers_successful


@pytest.mark.asyncio
async def test_brave_http_429_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rate-limit (429) errors are surfaced in SearchResult.errors."""

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "HTTP 429 Too Many Requests"

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)

    result = await web_search("rate limited")
    assert any("429" in e for e in result.errors)
    assert "brave" not in result.providers_successful


@pytest.mark.asyncio
async def test_brave_malformed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Malformed JSON errors are surfaced in SearchResult.errors."""

    async def fake_brave(q: str, n: int) -> tuple[list[WebHit], str | None]:
        return [], "Malformed JSON response"

    _stub_other_providers(monkeypatch)
    monkeypatch.setattr(search_module, "_search_brave", fake_brave)

    result = await web_search("malformed query")
    assert any("Malformed JSON" in e for e in result.errors)
    assert "brave" not in result.providers_successful
