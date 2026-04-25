"""Parallel web search over Tavily, Brave Search API, and DDGS.

All three providers run concurrently via :func:`asyncio.gather`; DDG is
synchronous so it runs in a worker thread.

Hits that share a URL are **merged** into one :class:`WebHit` (combined
snippets, max score, comma-sorted ``source``) so no provider text is discarded.

Error handling is explicit (not swallowed): :class:`SearchResult` carries
``hits``, plus ``errors`` — a per-provider reason string for any provider that
did not run successfully (rate-limit, network error, …). The calling agent is
responsible for deciding whether partial results are good enough or whether to
fail the whole turn. :class:`search.web_search` never raises on provider
failure; it reports. ``TAVILY_API_KEY`` and ``BRAVE_API_KEY`` are required at
application settings load.
"""

from __future__ import annotations

import asyncio
import logging

from core.logging.app_logging import get_logger, log_event
from core.settings import settings
from tools.search_merge import _SNIPPET_MERGE_SEP
from tools.search_models import SearchResult, WebHit
from tools.search_providers import (
    merge_hits_by_url,
    search_brave,
    search_ddg,
    search_tavily,
)

logger = get_logger(__name__)

__all__ = [
    "_SNIPPET_MERGE_SEP",
    "SearchResult",
    "WebHit",
    "web_search",
]

# Backward-compatible aliases for tests
_search_tavily = search_tavily
_search_brave = search_brave
_search_ddg = search_ddg

_TAVILY_PROVIDER = "tavily"
_BRAVE_PROVIDER = "brave"
_DDG_PROVIDER = "duckduckgo"


async def web_search(
    query: str, max_results: int | None = None
) -> SearchResult:
    """Run Tavily + Brave + DuckDuckGo in parallel and return a
    :class:`SearchResult`.

    Never raises. Provider failures are recorded in ``SearchResult.errors`` so
    the caller can distinguish "the web had nothing to say about this query"
    (no hits, no errors) from "we literally could not reach any search backend"
    (no hits, every provider errored).
    """
    cap = (
        max_results if max_results is not None else settings.search_max_results
    )
    (
        (tav_hits, tav_err),
        (brave_hits, brave_err),
        (ddg_hits, ddg_err),
    ) = await asyncio.gather(
        _search_tavily(query, cap),
        _search_brave(query, cap),
        _search_ddg(query, cap),
    )
    errors: list[str] = [e for e in (tav_err, brave_err, ddg_err) if e]
    successful: list[str] = []
    if tav_err is None:
        successful.append(_TAVILY_PROVIDER)
    if brave_err is None:
        successful.append(_BRAVE_PROVIDER)
    if ddg_err is None:
        successful.append(_DDG_PROVIDER)
    merged = merge_hits_by_url(tav_hits, brave_hits, ddg_hits)[: cap * 3]
    if not merged and not errors:
        errors.append(
            "Search returned no URLs: providers finished without API/HTTP "
            "errors but produced zero hits (DuckDuckGo may rate-limit or "
            "block automated clients)."
        )
    logger.info(
        "web_search query=%r tavily=%s brave=%s ddg=%s merged=%s errors=%s",
        query,
        len(tav_hits),
        len(brave_hits),
        len(ddg_hits),
        len(merged),
        errors,
    )
    top_hits = [
        {
            "url": h.url,
            "title": (h.title or "")[:120],
            "source": h.source,
            "score": h.score,
        }
        for h in merged[:30]
    ]
    log_event(
        logger,
        logging.INFO,
        "web_search.completed",
        query=query,
        tavily_hit_count=len(tav_hits),
        brave_hit_count=len(brave_hits),
        ddg_hit_count=len(ddg_hits),
        merged_returned=len(merged),
        providers_attempted=[_TAVILY_PROVIDER, _BRAVE_PROVIDER, _DDG_PROVIDER],
        providers_successful=successful,
        errors=errors,
        top_hits=top_hits,
    )
    return SearchResult(
        hits=merged,
        errors=errors,
        providers_attempted=[_TAVILY_PROVIDER, _BRAVE_PROVIDER, _DDG_PROVIDER],
        providers_successful=successful,
    )
