"""Live Brave Search API smoke tests.

Requires a valid ``BRAVE_API_KEY`` and intent to hit the network::

    BRAVE_LIVE=1 pytest tests/test_brave_live.py -n0 --no-cov -m integration

Without ``BRAVE_LIVE=1``, tests are skipped.
"""

from __future__ import annotations

import os
import time

import pytest

from a2a_research.tools import search as search_module
from a2a_research.tools.search import WebHit

# One xdist worker for this module: Brave free tier is ~1 req/s; parallel workers
# cause 429s under ``pytest -n auto``.
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
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_live_search_returns_hits() -> None:
    query = '"Agloe" New York copyright trap map'
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 1
    assert all(h.source == "brave" for h in hits)
    assert all(h.url.startswith(("http://", "https://")) for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_hit_structure() -> None:
    query = "Mpemba effect hot water freezing"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 1
    for hit in hits:
        assert hit.url.startswith(("http://", "https://"))
        assert isinstance(hit.title, str) and len(hit.title) > 0
        assert isinstance(hit.snippet, str) and len(hit.snippet) > 0
        assert hit.source == "brave"
        assert isinstance(hit.score, float)
        assert 0.0 <= hit.score <= 1.0


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_max_results_respected() -> None:
    query = "Python programming language"
    hits, err = await search_module._search_brave(query, max_results=3)
    assert err is None, f"Brave error: {err}"
    assert len(hits) <= 3
    if len(hits) > 0:
        assert all(h.source == "brave" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_multiple_queries_different_results() -> None:
    query1 = "Agloe New York copyright trap"
    query2 = "Mpemba effect thermodynamics"
    hits1, err1 = await search_module._search_brave(query1, max_results=5)
    hits2, err2 = await search_module._search_brave(query2, max_results=5)
    assert err1 is None, f"Brave error on query1: {err1}"
    assert err2 is None, f"Brave error on query2: {err2}"
    assert len(hits1) >= 1
    assert len(hits2) >= 1
    urls1 = {h.url for h in hits1}
    urls2 = {h.url for h in hits2}
    assert urls1 != urls2, "Different queries should return different URL sets"


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_unicode_query() -> None:
    query = "München Germany history"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 1
    assert all(h.source == "brave" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_special_chars_query() -> None:
    query = "C++ programming language"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 1
    assert all(h.source == "brave" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_nonsense_query() -> None:
    query = "xyzzyabc12345 notarealword"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert isinstance(hits, list)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_results_have_distinct_urls() -> None:
    query = "Python programming"
    hits, err = await search_module._search_brave(query, max_results=10)
    assert err is None, f"Brave error: {err}"
    urls = [h.url for h in hits]
    assert len(urls) == len(set(urls)), (
        "No duplicate URLs should appear in results"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_response_time_reasonable() -> None:
    query = "Agloe copyright trap"
    start = time.time()
    hits, err = await search_module._search_brave(query, max_results=5)
    elapsed = time.time() - start
    assert err is None, f"Brave error: {err}"
    assert elapsed < 15.0, f"Search took {elapsed:.2f}s, expected < 15s"
    assert len(hits) >= 1


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_popular_query_many_results() -> None:
    query = "Python programming"
    hits, err = await search_module._search_brave(query, max_results=10)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 3, "Popular query should return multiple hits"
    assert all(h.source == "brave" for h in hits)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1",
    reason="Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP tests.",
)
@pytest.mark.asyncio
async def test_brave_snippet_quality() -> None:
    query = "Mpemba effect"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert len(hits) >= 1
    assert _any_hit_mentions(hits, "mpemba"), (
        "Expected at least one hit's snippet/title to mention Mpemba; got: "
        + repr([(h.url, h.title[:80]) for h in hits])
    )
