"""Tavily search provider."""

from __future__ import annotations

import logging
from typing import Any

from a2a_research.logging.app_logging import get_logger, log_event
from a2a_research.settings import settings
from a2a_research.tools.search_models import WebHit

logger = get_logger(__name__)

_TAVILY_PROVIDER = "tavily"


async def search_tavily(
    query: str, max_results: int
) -> tuple[list[WebHit], str | None]:
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
        from tavily import AsyncTavilyClient

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
