"""Live Tavily API smoke tests.

Requires valid ``TAVILY_API_KEY`` and ``BRAVE_API_KEY`` for full-stack tests::

    TAVILY_LIVE=1 pytest tests/test_tavily_live.py -n0 --no-cov -m integration

Without ``TAVILY_LIVE=1``, tests are skipped (avoids calling APIs with CI placeholder keys).
"""

from __future__ import annotations

import os

import pytest

from a2a_research.tools import search as search_module
from a2a_research.tools.search import WebHit, web_search

# Share a worker with ``test_brave_live`` so Brave is not called from multiple
# processes (free-tier rate limit).
pytestmark = pytest.mark.xdist_group("live_search_providers")


def _hit_text(hit: WebHit) -> str:
    return f"{hit.url} {hit.title} {hit.snippet}".lower()


def _any_hit_mentions(hits: list[WebHit], *needles: str) -> bool:
    """True if some hit contains every needle (case-insensitive)."""
    texts = [_hit_text(h) for h in hits]
    lowered = [n.lower() for n in needles]
    return any(all(n in t for n in lowered) for t in texts)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_live_search_returns_hits() -> None:
    # Phantom "town" inserted as a copyright trap on maps; too specific to fake plausibly.
    query = '"Agloe" New York copyright trap map'
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    assert all(h.source == "tavily" for h in hits)
    assert all(h.url.startswith(("http://", "https://")) for h in hits)
    assert _any_hit_mentions(hits, "agloe"), (
        "Expected at least one result mentioning Agloe; got: "
        + repr([(h.url, h.title[:80]) for h in hits])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_web_search_includes_tavily_when_configured() -> None:
    # Obscure thermodynamics puzzle; title/snippet should name it, unlike generic "science" hits.
    result = await web_search('"Mpemba effect" hot water freezing paradox', max_results=5)
    assert "tavily" in result.providers_successful
    assert "brave" in result.providers_successful
    assert any("tavily" in h.source for h in result.hits)
    assert _any_hit_mentions(result.hits, "mpemba"), (
        "Expected merged hits to mention Mpemba; got: "
        + repr([(h.source, h.url, (h.title or "")[:100]) for h in result.hits])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_hit_structure() -> None:
    query = "Mpemba effect thermodynamics"
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    for hit in hits:
        assert hit.url.startswith(("http://", "https://"))
        assert isinstance(hit.title, str) and len(hit.title) > 0
        assert isinstance(hit.snippet, str) and len(hit.snippet) > 0
        assert hit.source == "tavily"
        assert isinstance(hit.score, float)
        assert hit.score >= 0.0


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_max_results_respected() -> None:
    query = "Python programming language"
    hits, err = await search_module._search_tavily(query, max_results=3)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) <= 3
    if len(hits) > 0:
        assert all(h.source == "tavily" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_score_positive() -> None:
    query = "Python programming"
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    assert any(h.score > 0 for h in hits), (
        "Expected at least one hit with positive score; got: "
        + repr([(h.url, h.score) for h in hits])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_unicode_query() -> None:
    query = "München Germany history"
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    assert all(h.source == "tavily" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_popular_query() -> None:
    query = "Python programming"
    hits, err = await search_module._search_tavily(query, max_results=10)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 3, "Popular query should return multiple hits"
    assert all(h.source == "tavily" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_web_search_merge_providers_live() -> None:
    result = await web_search("Agloe copyright trap map", max_results=5)
    assert "tavily" in result.providers_successful
    assert "brave" in result.providers_successful
    multi_source_hits = [h for h in result.hits if "," in h.source]
    assert len(multi_source_hits) >= 1, (
        "Expected at least one hit from multiple providers (comma in source); got: "
        + repr([(h.source, h.url) for h in result.hits])
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
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
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
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
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
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
                "failed" in error.lower() or "error" in error.lower() or "timeout" in error.lower()
            )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_web_search_providers_metadata() -> None:
    result = await web_search("Python programming", max_results=5)
    assert set(result.providers_attempted) == {"tavily", "brave", "duckduckgo"}
    assert set(result.providers_successful).issubset(set(result.providers_attempted))
    assert result.any_provider_succeeded == bool(result.providers_successful)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("TAVILY_LIVE") != "1",
    reason="Set TAVILY_LIVE=1 and real TAVILY_API_KEY / BRAVE_API_KEY for live HTTP tests.",
)
@pytest.mark.asyncio
async def test_tavily_snippet_relevance() -> None:
    query = "Mpemba effect"
    hits, err = await search_module._search_tavily(query, max_results=5)
    assert err is None, f"Tavily error: {err}"
    assert len(hits) >= 1
    assert _any_hit_mentions(hits, "mpemba"), (
        "Expected at least one snippet to mention the search term; got: "
        + repr([(h.url, h.snippet[:120]) for h in hits])
    )
