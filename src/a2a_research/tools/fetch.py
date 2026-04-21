"""Fetch + extract main text from a URL using trafilatura.

Sync operations are wrapped in :func:`asyncio.to_thread` so the Reader agent
can fan-out over many URLs in parallel without blocking the event loop.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from pydantic import BaseModel, Field

from a2a_research.app_logging import get_logger, log_event

logger = get_logger(__name__)

__all__ = ["PageContent", "fetch_and_extract", "fetch_many"]


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


def _fetch_sync(url: str, max_chars: int) -> PageContent:
    try:
        from trafilatura import extract, fetch_url
    except ImportError as exc:
        return PageContent(url=url, error=f"trafilatura unavailable: {exc}")
    try:
        downloaded = fetch_url(url)
    except Exception as exc:
        return PageContent(url=url, error=f"fetch failed: {exc}")
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
        transport="trafilatura.fetch_url",
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
