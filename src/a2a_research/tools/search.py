"""Parallel web search over Tavily + DDGS.

Both providers run concurrently via :func:`asyncio.gather`; DDG is synchronous
so it runs in a worker thread.

Error handling is explicit (not swallowed): :class:`SearchResult` carries
``hits``, plus ``errors`` — a per-provider reason string for any provider that
did not run successfully (blank API key, rate-limit, network error, …). The
calling agent is responsible for deciding whether partial results are good
enough or whether to fail the whole turn. :class:`search.web_search` never
raises on provider failure; it reports.
"""

from __future__ import annotations

import asyncio
from typing import Any

from pydantic import BaseModel, Field

from a2a_research.app_logging import get_logger
from a2a_research.settings import settings

logger = get_logger(__name__)

__all__ = ["SearchResult", "WebHit", "web_search"]

_TAVILY_PROVIDER = "tavily"
_DDG_PROVIDER = "duckduckgo"


class WebHit(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    source: str = Field(default="unknown", description="tavily | duckduckgo")
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
    if not api_key:
        return [], "Tavily disabled (TAVILY_API_KEY is blank in .env)."
    try:
        from tavily import AsyncTavilyClient  # type: ignore[attr-defined]

        client = AsyncTavilyClient(api_key=api_key)
        response: dict[str, Any] = await client.search(
            query=query, max_results=max_results, search_depth="basic"
        )
    except Exception as exc:
        logger.warning("Tavily search failed query=%r error=%s", query, exc)
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
    try:
        hits = await asyncio.to_thread(_search_ddg_sync, query, max_results)
    except Exception as exc:
        logger.warning("DuckDuckGo search failed query=%r error=%s", query, exc)
        return [], f"DuckDuckGo request failed: {exc}"
    return hits, None


def _merge_dedupe(tavily: list[WebHit], ddg: list[WebHit]) -> list[WebHit]:
    by_url: dict[str, WebHit] = {}
    for hit in tavily:
        by_url[hit.url] = hit
    for hit in ddg:
        by_url.setdefault(hit.url, hit)
    return sorted(by_url.values(), key=lambda h: (-h.score, h.source))


async def web_search(query: str, max_results: int | None = None) -> SearchResult:
    """Run Tavily + DuckDuckGo in parallel and return a :class:`SearchResult`.

    Never raises. Provider failures are recorded in ``SearchResult.errors`` so
    the caller can distinguish "the web had nothing to say about this query"
    (no hits, no errors) from "we literally could not reach any search backend"
    (no hits, every provider errored).
    """
    cap = max_results if max_results is not None else settings.search_max_results
    (tav_hits, tav_err), (ddg_hits, ddg_err) = await asyncio.gather(
        _search_tavily(query, cap), _search_ddg(query, cap)
    )
    errors: list[str] = [e for e in (tav_err, ddg_err) if e]
    successful: list[str] = []
    if tav_err is None:
        successful.append(_TAVILY_PROVIDER)
    if ddg_err is None:
        successful.append(_DDG_PROVIDER)
    merged = _merge_dedupe(tav_hits, ddg_hits)[: cap * 2]
    logger.info(
        "web_search query=%r tavily=%s ddg=%s merged=%s errors=%s",
        query,
        len(tav_hits),
        len(ddg_hits),
        len(merged),
        errors,
    )
    return SearchResult(
        hits=merged,
        errors=errors,
        providers_attempted=[_TAVILY_PROVIDER, _DDG_PROVIDER],
        providers_successful=successful,
    )
