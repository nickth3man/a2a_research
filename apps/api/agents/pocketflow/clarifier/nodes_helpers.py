"""Helpers for Clarifier nodes."""

from __future__ import annotations

from typing import Any


def _is_likely_unambiguous(query: str) -> bool:
    """Heuristic: short queries without comparison/opinion tokens are likely
    unambiguous.
    """
    lowered = query.lower()
    ambiguous_tokens = (
        " or ",
        " vs ",
        " versus ",
        " better ",
        " best ",
        " compare ",
        " difference ",
        " between ",
        " should i ",
        " pros and cons ",
        " opinion ",
        " think ",
        " believe ",
        " feel ",
    )
    return len(query) < 120 and not any(
        token in lowered for token in ambiguous_tokens
    )


def _extract_disambiguations(
    data: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Extract and normalize disambiguation list from LLM JSON output."""
    if not isinstance(data, dict):
        return []
    raw = data.get("disambiguations")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            interp = str(item.get("interpretation") or "").strip()
            if interp:
                try:
                    conf = float(item.get("confidence", 0.5))
                except (TypeError, ValueError):
                    conf = 0.5
                result.append(
                    {
                        "interpretation": interp,
                        "confidence": max(0.0, min(1.0, conf)),
                    }
                )
        elif isinstance(item, str) and item.strip():
            result.append({"interpretation": item.strip(), "confidence": 0.5})
    return result
