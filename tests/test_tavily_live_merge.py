"""Live Tavily merge, dedup, and metadata tests."""

from __future__ import annotations

import os

import pytest

from a2a_research.tools.search import web_search

pytestmark = pytest.mark.xdist_group("live_search_providers")

_HAS_KEY = bool(
    os.environ.get("TAVILY_API_KEY") and os.environ.get("BRAVE_API_KEY")
)
_SKIP_REASON = (
    "Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live"
    " HTTP tests."
)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_web_search_merge_providers_live() -> None:
    result = await web_search("Agloe copyright trap map", max_results=5)
    assert "tavily" in result.providers_successful
    assert "brave" in result.providers_successful
    multi_source_hits = [h for h in result.hits if "," in h.source]
    assert len(multi_source_hits) >= 1, (
        "Expected at least one hit from multiple providers (comma in source);"
        " got: " + repr([(h.source, h.url) for h in result.hits])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_web_search_deduplication_live() -> None:
    result = await web_search("Google", max_results=10)
    urls = [h.url for h in result.hits]
    assert len(urls) == len(set(urls)), (
        "No URL should appear twice in merged results; duplicates: "
        + repr([u for u in urls if urls.count(u) > 1])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_web_search_result_ordering() -> None:
    result = await web_search("Python programming language", max_results=10)
    assert len(result.hits) >= 2, "Need at least 2 hits to verify ordering"
    scores = [h.score for h in result.hits]
    assert scores == sorted(scores, reverse=True), (
        "Hits should be sorted by descending score; got: " + repr(scores)
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_web_search_error_field_structure() -> None:
    result = await web_search("Mpemba effect", max_results=5)
    if result.any_provider_succeeded and len(result.errors) == 0:
        pass
    else:
        for error in result.errors:
            assert isinstance(error, str) and len(error) > 0
            assert (
                "failed" in error.lower()
                or "error" in error.lower()
                or "timeout" in error.lower()
            )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_web_search_providers_metadata() -> None:
    result = await web_search("Python programming", max_results=5)
    assert set(result.providers_attempted) == {"tavily", "brave", "duckduckgo"}
    assert set(result.providers_successful).issubset(
        set(result.providers_attempted)
    )
    assert result.any_provider_succeeded == bool(result.providers_successful)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_tavily_snippet_relevance() -> None:
    from a2a_research.tools import search as search_module
    from a2a_research.tools.search import WebHit

    def _hit_text(hit: WebHit) -> str:
        return f"{hit.url} {hit.title} {hit.snippet}".lower()

    def _any_hit_mentions(hits: list[WebHit], *needles: str) -> bool:
        texts = [_hit_text(h) for h in hits]
        lowered = [n.lower() for n in needles]
        return any(all(n in t for n in lowered) for t in texts)

    query = "Mpemba effect"
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    assert _any_hit_mentions(hits, "mpemba"), (
        "Expected at least one snippet to mention the search term; got: "
        + repr([(h.url, h.snippet[:120]) for h in hits])
    )
