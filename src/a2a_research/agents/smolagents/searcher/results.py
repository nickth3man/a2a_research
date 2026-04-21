"""Searcher result parsing and fallback merge logic."""

from __future__ import annotations

import asyncio
from typing import Any

from a2a_research.utils.json_utils import parse_json_safely
from a2a_research.tools import WebHit, web_search


def parse_search_results(raw_output: str) -> dict[str, Any]:
    """Parse raw agent output and return hit/error/query data."""
    data = parse_json_safely(raw_output)
    by_url: dict[str, WebHit] = {}
    errors: list[str] = []
    seen_errors: set[str] = set()
    successful_providers: set[str] = set()

    raw_hits_any = data.get("hits")
    raw_hits: list[object] = (
        raw_hits_any if isinstance(raw_hits_any, list) else []
    )
    for raw_hit in raw_hits:
        if not isinstance(raw_hit, dict):
            continue
        hit = WebHit.model_validate(raw_hit)
        by_url.setdefault(hit.url, hit)
        successful_providers.add(hit.source)

    raw_errors_any = data.get("errors")
    raw_errors: list[object] = (
        raw_errors_any if isinstance(raw_errors_any, list) else []
    )
    for err in raw_errors:
        if isinstance(err, str) and err not in seen_errors:
            seen_errors.add(err)
            errors.append(err)

    queries_used_raw = data.get("queries_used")
    queries_used = (
        [
            item.strip()
            for item in queries_used_raw
            if isinstance(item, str) and item.strip()
        ]
        if isinstance(queries_used_raw, list)
        else []
    )
    return {
        "by_url": by_url,
        "errors": errors,
        "successful_providers": successful_providers,
        "queries_used": queries_used,
    }


async def merge_with_fallback(
    by_url: dict[str, WebHit],
    errors: list[str],
    successful_providers: set[str],
    queries: list[str],
) -> tuple[dict[str, WebHit], list[str], set[str]]:
    """If no hits or errors, run direct web_search fallback and merge."""
    if not by_url and not errors:
        fallback_results = await asyncio.gather(
            *[web_search(query) for query in queries],
            return_exceptions=False,
        )
        for result in fallback_results:
            for hit in result.hits:
                by_url.setdefault(hit.url, hit)
            errors.extend(
                err for err in result.errors if err not in errors
            )
            successful_providers.update(result.providers_successful)
        if not by_url and not errors:
            errors.append("Searcher agent returned no usable hits.")
    return by_url, errors, successful_providers
