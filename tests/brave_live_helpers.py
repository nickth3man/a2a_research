"""Shared helpers for Brave live tests."""

from __future__ import annotations

import os

from a2a_research.tools.search import WebHit

_HAS_KEY = bool(os.environ.get("BRAVE_API_KEY"))
_SKIP_REASON = (
    "Set BRAVE_LIVE=1 and a real BRAVE_API_KEY to run live Brave HTTP"
    " tests."
)


def _hit_text(hit: WebHit) -> str:
    return f"{hit.url} {hit.title} {hit.snippet}".lower()


def _any_hit_mentions(hits: list[WebHit], *needles: str) -> bool:
    """True if some hit contains every needle (case-insensitive)."""
    texts = [_hit_text(h) for h in hits]
    lowered = [n.lower() for n in needles]
    return any(all(n in t for n in lowered) for t in texts)
