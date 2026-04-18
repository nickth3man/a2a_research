"""Parallel web search over Tavily, Brave Search API, and DDGS.

All three providers run concurrently via :func:`asyncio.gather`; DDG is synchronous
so it runs in a worker thread.

Hits that share a URL are **merged** into one :class:`WebHit` (combined snippets,
max score, comma-sorted ``source``) so no provider text is discarded.

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
from typing import Any

import httpx
from pydantic import BaseModel, Field

from a2a_research.app_logging import get_logger, log_event
from a2a_research.settings import settings

logger = get_logger(__name__)

__all__ = ["SearchResult", "WebHit", "web_search"]

_TAVILY_PROVIDER = "tavily"
_BRAVE_PROVIDER = "brave"
_DDG_PROVIDER = "duckduckgo"

_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_SNIPPET_MERGE_SEP = "\n---\n"


class WebHit(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    source: str = Field(
        default="unknown",
        description="Single provider id or comma-sorted ids when merged (tavily, brave, duckduckgo).",
    )
    score: float = Field(default=0.0, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """Parallel search outcome for a single query."""

    hits: list[WebHit] = Field(default_factory=list)
    errors: list[str] = Field(
        default_factory=list,
        description="Per-provider failure reasons (one human-readable string per failed provider).",
    )
    providers_attempted: list[str] = Field(default_factory=list)
    providers_successful: list[str] = Field(default_factory=list)

    @property
    def any_provider_succeeded(self) -> bool:
        return bool(self.providers_successful)


async def _search_tavily(query: str, max_results: int) -> tuple[list[WebHit], str | None]:
    api_key = settings.tavily_api_key
    log_event(
        logger,
        logging.INFO,
        "search.provider_request",
        provider=_TAVILY_PROVIDER,
        endpoint="https://api.tavily.com/search",
        query=query,
        max_results=max_results,
    )
    try:
        from tavily import AsyncTavilyClient  # type: ignore[attr-defined]

        client = AsyncTavilyClient(api_key=api_key)
        response: dict[str, Any] = await client.search(
            query=query, max_results=max_results, search_depth="basic"
        )
    except Exception as exc:
        logger.warning("Tavily search failed query=%r error=%s", query, exc)
        log_event(
            logger,
            logging.INFO,
            "search.provider_response",
            provider=_TAVILY_PROVIDER,
            query=query,
            hit_count=0,
            error=str(exc),
        )
        return [], f"Tavily request failed: {exc}"
    hits: list[WebHit] = []
    for item in response.get("results") or []:
        url = item.get("url") or ""
        if not url:
            continue
        hits.append(
            WebHit(
                url=url,
                title=item.get("title") or "",
                snippet=item.get("content") or "",
                source=_TAVILY_PROVIDER,
                score=float(item.get("score") or 0.0),
            )
        )
    log_event(
        logger,
        logging.INFO,
        "search.provider_response",
        provider=_TAVILY_PROVIDER,
        query=query,
        hit_count=len(hits),
    )
    return hits, None


async def _search_brave(query: str, max_results: int) -> tuple[list[WebHit], str | None]:
    api_key = settings.brave_api_key
    count = min(max_results, 20)
    log_event(
        logger,
        logging.INFO,
        "search.provider_request",
        provider=_BRAVE_PROVIDER,
        endpoint=_BRAVE_SEARCH_URL,
        query=query,
        max_results=max_results,
    )
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                _BRAVE_SEARCH_URL,
                params={"q": query, "count": count},
                headers={
                    "Accept": "application/json",
                    "X-Subscription-Token": api_key,
                },
                timeout=30.0,
            )
            text = response.text
            if response.status_code != 200:
                log_fn = logger.info if response.status_code == 429 else logger.warning
                log_fn(
                    "Brave search HTTP error query=%r status=%s body=%s",
                    query,
                    response.status_code,
                    text[:500],
                )
                log_event(
                    logger,
                    logging.INFO,
                    "search.provider_response",
                    provider=_BRAVE_PROVIDER,
                    query=query,
                    hit_count=0,
                    error=f"HTTP {response.status_code}",
                )
                return [], f"Brave request failed: HTTP {response.status_code} {text[:200]}"
            data: dict[str, Any] = response.json()
    except Exception as exc:
        logger.warning("Brave search failed query=%r error=%s", query, exc)
        log_event(
            logger,
            logging.INFO,
            "search.provider_response",
            provider=_BRAVE_PROVIDER,
            query=query,
            hit_count=0,
            error=str(exc),
        )
        return [], f"Brave request failed: {exc}"

    hits: list[WebHit] = []
    for i, item in enumerate(data.get("web", {}).get("results") or []):
        url = item.get("url") or ""
        if not url:
            continue
        hits.append(
            WebHit(
                url=url,
                title=item.get("title") or "",
                snippet=item.get("description") or "",
                source=_BRAVE_PROVIDER,
                score=max(0.0, 1.0 - i * 0.01),
            )
        )
    log_event(
        logger,
        logging.INFO,
        "search.provider_response",
        provider=_BRAVE_PROVIDER,
        query=query,
        hit_count=len(hits),
    )
    return hits, None


def _search_ddg_sync(query: str, max_results: int) -> list[WebHit]:
    from ddgs import DDGS

    raw = DDGS().text(query, max_results=max_results) or []
    hits: list[WebHit] = []
    for item in raw:
        url = item.get("href") or item.get("url") or ""
        if not url:
            continue
        hits.append(
            WebHit(
                url=url,
                title=item.get("title") or "",
                snippet=item.get("body") or "",
                source=_DDG_PROVIDER,
                score=0.0,
            )
        )
    return hits


async def _search_ddg(query: str, max_results: int) -> tuple[list[WebHit], str | None]:
    log_event(
        logger,
        logging.INFO,
        "search.provider_request",
        provider=_DDG_PROVIDER,
        endpoint="https://html.duckduckgo.com/html/",
        query=query,
        max_results=max_results,
    )
    try:
        hits = await asyncio.to_thread(_search_ddg_sync, query, max_results)
    except Exception as exc:
        logger.warning("DuckDuckGo search failed query=%r error=%s", query, exc)
        log_event(
            logger,
            logging.INFO,
            "search.provider_response",
            provider=_DDG_PROVIDER,
            query=query,
            hit_count=0,
            error=str(exc),
        )
        return [], f"DuckDuckGo request failed: {exc}"
    log_event(
        logger,
        logging.INFO,
        "search.provider_response",
        provider=_DDG_PROVIDER,
        query=query,
        hit_count=len(hits),
    )
    return hits, None


def _merge_hits_by_url(*lists: list[WebHit]) -> list[WebHit]:
    """Merge hits that share a URL: combine snippets, max score, sorted sources."""
    buckets: dict[str, list[WebHit]] = {}
    for lst in lists:
        for hit in lst:
            buckets.setdefault(hit.url, []).append(hit)
    merged: list[WebHit] = []
    for url, hits in buckets.items():
        sources: set[str] = set()
        for h in hits:
            for part in h.source.split(","):
                p = part.strip()
                if p:
                    sources.add(p)
        snippets: list[str] = []
        seen_snippet: set[str] = set()
        for h in hits:
            s = (h.snippet or "").strip()
            if s and s not in seen_snippet:
                seen_snippet.add(s)
                snippets.append(s)
        title = ""
        for h in hits:
            t = (h.title or "").strip()
            if len(t) > len(title):
                title = t
        score = max((h.score for h in hits), default=0.0)
        snippet = _SNIPPET_MERGE_SEP.join(snippets)
        source = ",".join(sorted(sources))
        merged.append(WebHit(url=url, title=title, snippet=snippet, source=source, score=score))
    return sorted(merged, key=lambda h: (-h.score, h.url))


async def web_search(query: str, max_results: int | None = None) -> SearchResult:
    """Run Tavily + Brave + DuckDuckGo in parallel and return a :class:`SearchResult`.

    Never raises. Provider failures are recorded in ``SearchResult.errors`` so
    the caller can distinguish "the web had nothing to say about this query"
    (no hits, no errors) from "we literally could not reach any search backend"
    (no hits, every provider errored).
    """
    cap = max_results if max_results is not None else settings.search_max_results
    (tav_hits, tav_err), (brave_hits, brave_err), (ddg_hits, ddg_err) = await asyncio.gather(
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
    merged = _merge_hits_by_url(tav_hits, brave_hits, ddg_hits)[: cap * 3]
    if not merged and not errors:
        errors.append(
            "Search returned no URLs: providers finished without API/HTTP errors but "
            "produced zero hits (DuckDuckGo may rate-limit or block automated clients)."
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
        {"url": h.url, "title": (h.title or "")[:120], "source": h.source, "score": h.score}
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
