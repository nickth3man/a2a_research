"""Live Brave Search API smoke tests.

Requires a valid ``BRAVE_API_KEY`` and intent to hit the network::

    BRAVE_LIVE=1 pytest tests/test_brave_live.py -n0 --no-cov -m integration

Without ``BRAVE_LIVE=1``, tests are skipped.
"""

from __future__ import annotations

import os

import pytest

from a2a_research.tools import search as search_module


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
