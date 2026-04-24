"""Tests for trafilatura-backed page fetch + extract."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

import httpx
import pytest

from a2a_research.backend.tools import fetch as fetch_module
from a2a_research.backend.tools.fetch import (
    PageContent,
    fetch_and_extract,
    fetch_many,
)

if TYPE_CHECKING:
    from collections.abc import Callable


def call_fetch_sync(url: str, max_chars: int) -> PageContent:
    fetch_sync_name = "_fetch_sync"
    fetch_sync = cast(
        "Callable[[str, int], PageContent]",
        getattr(fetch_module, fetch_sync_name),
    )
    return fetch_sync(url, max_chars)


def call_download_url(url: str) -> tuple[str | None, str | None]:
    download_url_name = "_download_url"
    download_url = cast(
        "Callable[[str], tuple[str | None, str | None]]",
        getattr(fetch_module, download_url_name),
    )
    return download_url(url)


def allow_public_dns(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_getaddrinfo(*args: Any, **kwargs: Any) -> list[tuple[Any, ...]]:
        return [
            (
                fetch_module.socket.AF_INET,
                fetch_module.socket.SOCK_STREAM,
                0,
                "",
                ("93.184.216.34", 443),
            )
        ]

    monkeypatch.setattr(fetch_module.socket, "getaddrinfo", fake_getaddrinfo)


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

    def fake_download_url(url: str) -> tuple[str | None, str | None]:
        called["url"] = url
        return "<html><body><h1>T</h1><p>Body</p></body></html>", None

    def fake_extract(downloaded: str, **kwargs: Any) -> str:
        called["kwargs"] = kwargs
        return "# T\n\nBody"

    monkeypatch.setattr(fetch_module, "_download_url", fake_download_url)
    monkeypatch.setattr(_traf, "extract", fake_extract)
    page = call_fetch_sync("https://t.example", 8000)
    assert page.error is None
    assert page.title == "T"
    assert page.word_count > 0
    assert called["url"] == "https://t.example"
    assert called["kwargs"].get("output_format") == "markdown"


def test_fetch_sync_handles_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_download_url(url: str) -> tuple[str | None, str | None]:
        return None, None

    monkeypatch.setattr(fetch_module, "_download_url", fake_download_url)
    page = call_fetch_sync("https://empty.example", 8000)
    assert page.error and "empty" in page.error


def test_fetch_sync_blocks_non_http_urls() -> None:
    page = call_fetch_sync("file:///etc/passwd", 8000)
    assert page.error == "URL scheme must be http or https"


def test_fetch_sync_blocks_localhost_literal() -> None:
    page = call_fetch_sync("http://127.0.0.1:8000/private", 8000)
    assert page.error == "URL resolves to a non-public address"


def test_fetch_sync_blocks_private_dns_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_private_getaddrinfo(
        *args: Any, **kwargs: Any
    ) -> list[tuple[Any, ...]]:
        return [
            (
                fetch_module.socket.AF_INET,
                fetch_module.socket.SOCK_STREAM,
                0,
                "",
                ("10.0.0.10", 443),
            )
        ]

    monkeypatch.setattr(
        fetch_module.socket,
        "getaddrinfo",
        fake_private_getaddrinfo,
    )
    page = call_fetch_sync("https://example.test", 8000)
    assert page.error == "URL resolves to a non-public address"


def test_download_url_blocks_redirect_to_localhost(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    allow_public_dns(monkeypatch)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "safe.example":
            return httpx.Response(
                status_code=302,
                headers={"Location": "http://127.0.0.1/private"},
            )
        return httpx.Response(200, text="private")

    transport = httpx.MockTransport(handler)
    original_client = fetch_module.httpx.Client

    def fake_client(**kwargs: Any) -> httpx.Client:
        return original_client(transport=transport, **kwargs)

    monkeypatch.setattr(fetch_module.httpx, "Client", fake_client)
    downloaded, error = call_download_url("https://safe.example")
    assert downloaded is None
    assert error == "URL resolves to a non-public address"
