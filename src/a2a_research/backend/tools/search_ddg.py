"""DuckDuckGo search provider."""

from __future__ import annotations

import asyncio
import logging

from a2a_research.backend.core.logging.app_logging import get_logger, log_event
from a2a_research.backend.tools.search_models import WebHit

logger = get_logger(__name__)

_DDG_PROVIDER = "duckduckgo"


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


async def search_ddg(
    query: str, max_results: int
) -> tuple[list[WebHit], str | None]:
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
        logger.warning(
            "DuckDuckGo search failed query=%r error=%s", query, exc
        )
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
