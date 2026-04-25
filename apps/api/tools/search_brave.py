"""Brave search provider."""

from __future__ import annotations

import asyncio
import logging
import threading
import time as _time
from typing import Any

import httpx

from core.logging.app_logging import get_logger, log_event
from core.models.enums import AgentRole
from core.progress import (
    current_session_id,
    emit_rate_limit,
)
from core.settings import settings
from tools.search_models import WebHit

logger = get_logger(__name__)

_BRAVE_PROVIDER = "brave"
_BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
_BRAVE_MIN_INTERVAL_SEC = 1.1
_BRAVE_MAX_RETRIES = 3
_brave_lock = threading.Lock()
_brave_last_call_ts = 0.0


async def _brave_throttle() -> None:
    """Rate-limit Brave requests to _BRAVE_MIN_INTERVAL_SEC between calls.

    Uses a threading.Lock (not asyncio.Lock) so it works across event loops
    created by asyncio.to_thread → new_event_loop in the smolagents path.
    The slot-reservation pattern ensures correct serialization without holding
    the lock across the async sleep.
    """
    global _brave_last_call_ts
    delay = 0.0
    with _brave_lock:
        now = _time.monotonic()
        gap = now - _brave_last_call_ts
        if gap < _BRAVE_MIN_INTERVAL_SEC:
            delay = _BRAVE_MIN_INTERVAL_SEC - gap
            _brave_last_call_ts = now + delay
        else:
            _brave_last_call_ts = now
    if delay > 0:
        emit_rate_limit(
            AgentRole.SEARCHER,
            provider="brave",
            attempt=0,
            max_attempts=_BRAVE_MAX_RETRIES,
            delay_sec=delay,
            reason="client throttle",
            session_id=current_session_id(),
        )
        await asyncio.sleep(delay)


def _parse_retry_after(headers: httpx.Headers, attempt: int) -> float:
    raw = headers.get("retry-after")
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return min(2.0**attempt, 8.0)


async def search_brave(
    query: str, max_results: int
) -> tuple[list[WebHit], str | None]:
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
    response: httpx.Response | None = None
    text = ""
    try:
        async with httpx.AsyncClient() as client:
            for attempt in range(_BRAVE_MAX_RETRIES + 1):
                await _brave_throttle()
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
                if (
                    response.status_code != 429
                    or attempt == _BRAVE_MAX_RETRIES
                ):
                    break
                delay = _parse_retry_after(response.headers, attempt)
                logger.info(
                    "Brave 429 query=%r attempt=%s retry_in=%.2fs",
                    query,
                    attempt + 1,
                    delay,
                )
                emit_rate_limit(
                    AgentRole.SEARCHER,
                    provider="brave",
                    attempt=attempt + 1,
                    max_attempts=_BRAVE_MAX_RETRIES,
                    delay_sec=delay,
                    reason=f"HTTP 429 query={query}",
                    session_id=current_session_id(),
                )
                await asyncio.sleep(delay)
            if response is None:
                return (
                    [],
                    "Brave request failed before receiving a response",
                )
            if response.status_code != 200:
                log_fn = (
                    logger.info
                    if response.status_code == 429
                    else logger.warning
                )
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
                return (
                    [],
                    (
                        f"Brave request failed: HTTP {response.status_code} "
                        f"{text[:200]}"
                    ),
                )
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
