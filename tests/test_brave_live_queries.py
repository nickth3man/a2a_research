"""Live Brave Search API query-specific behavior tests.

Requires a valid ``BRAVE_API_KEY`` and intent to hit the network::

    BRAVE_LIVE=1 pytest tests/test_brave_live_queries.py -n0 --no-cov
    -m integration

Without ``BRAVE_LIVE=1``, tests are skipped.
"""

from __future__ import annotations

import os

import pytest

from a2a_research.tools import search as search_module

from tests.brave_live_helpers import _HAS_KEY, _SKIP_REASON, _any_hit_mentions

pytestmark = pytest.mark.xdist_group("live_search_providers")


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    assert urls1 != urls2, (
        "Different queries should return different URL sets"
    )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
)
@pytest.mark.asyncio
async def test_brave_nonsense_query() -> None:
    query = "xyzzyabc12345 notarealword"
    hits, err = await search_module._search_brave(query, max_results=5)
    assert err is None, f"Brave error: {err}"
    assert isinstance(hits, list)


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
