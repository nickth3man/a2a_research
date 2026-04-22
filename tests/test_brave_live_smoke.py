"""Live Brave Search API smoke tests.

Requires a valid ``BRAVE_API_KEY`` and intent to hit the network::

    BRAVE_LIVE=1 pytest tests/test_brave_live_smoke.py -n0 --no-cov
    -m integration

Without ``BRAVE_LIVE=1``, tests are skipped.
"""

from __future__ import annotations

import os
import time

import pytest

from a2a_research.tools import search as search_module
from tests.brave_live_helpers import _HAS_KEY, _SKIP_REASON

pytestmark = pytest.mark.xdist_group("live_search_providers")


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
    os.environ.get("BRAVE_LIVE") != "1" and not _HAS_KEY,
    reason=_SKIP_REASON,
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
