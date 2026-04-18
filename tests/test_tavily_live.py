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
