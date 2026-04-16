"""Deterministic fallbacks used when an LLM provider is unavailable or returns empty output."""

from __future__ import annotations

from typing import Any

from a2a_research.models import Claim, Verdict


def fallback_research_summary(query: str, chunks: list[Any]) -> str:
    """Assemble a terse, provider-independent summary from the first few chunks."""
    if not chunks:
        return f"No retrieved evidence was available for the query: {query}"

    summary_lines = [f"Fallback research summary for query: {query}"]
    for rc in chunks[:3]:
        summary_lines.append(
            f"- source={rc.chunk.source} score={rc.score:.3f}: {rc.chunk.content[:180].strip()}"
        )
    return "\n".join(summary_lines)


def fallback_verified_claims(claims: list[Claim], reason: str) -> list[Claim]:
    """Return copies of ``claims`` degraded to ``INSUFFICIENT_EVIDENCE``."""
    return [
        claim.model_copy(
            update={
                "verdict": Verdict.INSUFFICIENT_EVIDENCE,
                "confidence": 0.0,
                "sources": [],
                "evidence_snippets": [reason],
            }
        )
        for claim in claims
    ]
