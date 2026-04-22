"""Formatting utilities for UI components."""

from __future__ import annotations

from urllib.parse import urlparse

from a2a_research.backend.core.models import Verdict


def format_source_display(src: str) -> str:
    """Format a URL or source identifier for compact display."""
    if src.startswith(("http://", "https://")):
        parsed = urlparse(src)
        host = parsed.netloc or src
        path = (parsed.path or "").rstrip("/")
        if not path or path == "/":
            return host
        tail = path.rsplit("/", 1)[-1][:60]
        return f"{host}/{tail}" if tail else host
    return src.replace("_", " ").replace("-", " ").title()


def format_claim_verdict(verdict: Verdict) -> str:
    """Render a verdict as a short label with a status glyph."""
    if verdict == Verdict.SUPPORTED:
        return "[SUPPORTED]"
    if verdict == Verdict.REFUTED:
        return "[REFUTED]"
    if verdict == Verdict.NEEDS_MORE_EVIDENCE:
        return "[NEEDS MORE]"
    return "[INSUFFICIENT]"


def format_confidence(confidence: float) -> str:
    return f"{confidence:.0%}"
