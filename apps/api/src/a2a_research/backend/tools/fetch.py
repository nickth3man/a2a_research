"""Fetch + extract main text from a URL using trafilatura.

Sync operations are wrapped in :func:`asyncio.to_thread` so the Reader agent
can fan-out over many URLs in parallel without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import socket
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from pydantic import BaseModel, Field

from a2a_research.backend.core.logging.app_logging import get_logger, log_event

logger = get_logger(__name__)

__all__ = ["PageContent", "fetch_and_extract", "fetch_many"]

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_MAX_REDIRECTS = 5


class PageContent(BaseModel):
    url: str
    title: str = ""
    markdown: str = ""
    word_count: int = 0
    error: str | None = Field(
        default=None, description="Non-None when fetch or extraction failed."
    )


def _extract_title(markdown: str) -> str:
    match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    if match:
        return match.group(1).strip()[:200]
    first_line = markdown.strip().split("\n", 1)[0]
    return first_line.strip()[:200]


def _is_public_address(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _validate_fetch_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return "URL scheme must be http or https"
    if not parsed.hostname:
        return "URL must include a hostname"
    host = parsed.hostname
    try:
        if not _is_public_address(host):
            return "URL resolves to a non-public address"
    except ValueError:
        pass
    try:
        addresses = {
            str(item[4][0])
            for item in socket.getaddrinfo(
                host, parsed.port or 443, type=socket.SOCK_STREAM
            )
        }
    except socket.gaierror as exc:
        return f"URL hostname could not be resolved: {exc}"
    if not addresses:
        return "URL hostname resolved no addresses"
    if not all(_is_public_address(address) for address in addresses):
        return "URL resolves to a non-public address"
    return None


def _download_url(url: str) -> tuple[str | None, str | None]:
    current_url = url.strip()
    headers = {"User-Agent": "a2a-research-fetch/1.0"}
    with httpx.Client(follow_redirects=False, timeout=20.0) as client:
        for _ in range(_MAX_REDIRECTS + 1):
            if validation_error := _validate_fetch_url(current_url):
                return None, validation_error
            try:
                response = client.get(current_url, headers=headers)
            except httpx.HTTPError as exc:
                return None, f"fetch failed: {exc}"

            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    return None, "redirect response missing Location header"
                current_url = urljoin(str(response.url), location)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                return None, f"fetch failed: {exc}"
            return response.text, None
    return None, "too many redirects"


def _fetch_sync(url: str, max_chars: int) -> PageContent:
    try:
        from trafilatura import extract
    except ImportError as exc:
        return PageContent(url=url, error=f"trafilatura unavailable: {exc}")
    downloaded, fetch_error = _download_url(url)
    if fetch_error:
        return PageContent(url=url, error=fetch_error)
    if not downloaded:
        return PageContent(url=url, error="fetch returned empty body")
    try:
        markdown: Any = extract(
            downloaded,
            output_format="markdown",
            favor_recall=False,
            fast=True,
        )
    except Exception as exc:
        return PageContent(url=url, error=f"extract failed: {exc}")
    if not markdown:
        return PageContent(url=url, error="extraction produced no text")
    text = str(markdown).strip()
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[…truncated…]"
    return PageContent(
        url=url,
        title=_extract_title(text),
        markdown=text,
        word_count=len(text.split()),
    )


async def fetch_and_extract(url: str, max_chars: int = 8000) -> PageContent:
    """Fetch ``url`` and return extracted markdown, or a PageContent with"""
    """error set."""
    page = await asyncio.to_thread(_fetch_sync, url, max_chars)
    if page.error:
        logger.debug("fetch_and_extract url=%s error=%s", url, page.error)
    else:
        logger.info("fetch_and_extract url=%s words=%s", url, page.word_count)
    return page


async def fetch_many(
    urls: list[str], max_chars: int = 8000
) -> list[PageContent]:
    """Fetch several URLs in parallel via ``asyncio.gather``."""
    log_event(
        logger,
        logging.INFO,
        "fetch.batch_start",
        url_count=len(urls),
        urls=urls,
        max_chars=max_chars,
        transport="httpx.safe_fetch",
    )
    tasks = [fetch_and_extract(url, max_chars) for url in urls]
    pages = list(await asyncio.gather(*tasks, return_exceptions=False))
    log_event(
        logger,
        logging.INFO,
        "fetch.batch_done",
        url_count=len(urls),
        ok_count=sum(1 for p in pages if not p.error),
        failed_count=sum(1 for p in pages if p.error),
        results=[
            {"url": p.url, "ok": not bool(p.error), "error": p.error}
            for p in pages
        ],
    )
    return pages
