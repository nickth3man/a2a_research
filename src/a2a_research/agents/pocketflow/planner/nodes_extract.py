"""Planner extraction helpers."""

from __future__ import annotations

from typing import Any

from a2a_research.models import (
    Claim,
    ClaimDAG,
    ClaimDependency,
    FreshnessWindow,
)


def _heuristic_strategy(query: str) -> str:
    lowered = query.lower()
    if any(
        token in lowered
        for token in ("compare", "vs", "versus", "better", "difference")
    ):
        return "comparative"
    if any(
        token in lowered
        for token in (
            "when",
            "timeline",
            "history",
            "date",
            "year",
            "launched",
            "before",
            "after",
        )
    ):
        return "temporal"
    return "factual"


def _extract(data: dict[str, Any] | None) -> tuple[list[Claim], list[str]]:
    if not isinstance(data, dict):
        return [], []
    claims: list[Claim] = []
    raw_claims = data.get("claims") or []
    if isinstance(raw_claims, list):
        for index, item in enumerate(raw_claims):
            if isinstance(item, dict):
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                raw_id = item.get("id") or f"c{index}"
                claims.append(
                    Claim(
                        id=str(raw_id),
                        text=text,
                        freshness=_extract_freshness(item, fallback_text=text),
                    )
                )
            elif isinstance(item, str) and item.strip():
                text = item.strip()
                claims.append(
                    Claim(
                        id=f"c{index}",
                        text=text,
                        freshness=_infer_freshness(text),
                    )
                )

    raw_seeds = data.get("seed_queries") or []
    seeds: list[str] = []
    if isinstance(raw_seeds, list):
        seeds = [
            str(item).strip()
            for item in raw_seeds
            if isinstance(item, str) and item.strip()
        ]
    return claims, seeds


def _extract_freshness(
    item: dict[str, Any], *, fallback_text: str
) -> FreshnessWindow:
    raw = item.get("freshness")
    if isinstance(raw, dict):
        try:
            return FreshnessWindow.model_validate(raw)
        except Exception:
            pass
    max_age_days = item.get("max_age_days")
    if isinstance(max_age_days, int) or (
        isinstance(max_age_days, str) and max_age_days.strip().isdigit()
    ):
        return FreshnessWindow(
            max_age_days=int(max_age_days),
            strict=bool(item.get("strict_freshness", False)),
            rationale=str(
                item.get("freshness_rationale")
                or "planner supplied max_age_days"
            ),
        )
    return _infer_freshness(fallback_text)


def _build_default_dag(claims: list[Claim]) -> ClaimDAG:
    return ClaimDAG(
        nodes=[claim.id for claim in claims],
        edges=[
            ClaimDependency(
                parent_id=claims[index - 1].id,
                child_id=claims[index].id,
                relation="refines",
            )
            for index in range(1, len(claims))
        ],
    )


def _infer_freshness(text: str) -> FreshnessWindow:
    lowered = text.lower()
    if any(
        token in lowered
        for token in (
            "today",
            "latest",
            "recent",
            "current",
            "2026",
            "2025",
            "new",
        )
    ):
        return FreshnessWindow(
            max_age_days=30,
            strict=True,
            rationale="Recency-sensitive claim inferred from query wording.",
        )
    if any(
        token in lowered
        for token in (
            "announced",
            "launched",
            "released",
            "quarter",
            "earnings",
        )
    ):
        return FreshnessWindow(
            max_age_days=365,
            strict=False,
            rationale="Time-bounded factual claim inferred from query"
            " wording.",
        )
    return FreshnessWindow(
        max_age_days=None,
        strict=False,
        rationale="No recency requirement inferred.",
    )
