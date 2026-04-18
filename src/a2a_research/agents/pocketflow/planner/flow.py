"""PocketFlow AsyncFlow wiring for the Planner."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pocketflow import AsyncFlow

from a2a_research.agents.pocketflow.planner.nodes import (
    ClassifyNode,
    ComparativeDecomposeNode,
    FactualDecomposeNode,
    FallbackNode,
    SeedQueryNode,
    TemporalDecomposeNode,
    TerminalNode,
)


if TYPE_CHECKING:
    from a2a_research.models import Claim

__all__ = ["build_planner_flow", "plan"]


def build_planner_flow() -> AsyncFlow[Any, Any]:
    classify = ClassifyNode()
    factual = FactualDecomposeNode()
    comparative = ComparativeDecomposeNode()
    temporal = TemporalDecomposeNode()
    seed = SeedQueryNode()
    fallback = FallbackNode()
    terminal = TerminalNode()

    _ = classify - "factual" >> factual
    _ = classify - "comparative" >> comparative
    _ = classify - "temporal" >> temporal
    _ = classify - "fallback" >> fallback

    _ = factual - "default" >> seed
    _ = factual - "fallback" >> fallback
    _ = comparative - "default" >> seed
    _ = comparative - "fallback" >> fallback
    _ = temporal - "default" >> seed
    _ = temporal - "fallback" >> fallback
    _ = seed - "default" >> terminal
    _ = fallback - "default" >> terminal

    return AsyncFlow(start=classify)


async def plan(query: str, *, session_id: str = "") -> tuple[list[Claim], list[str]]:
    """Run the Planner flow and return (claims, seed_queries)."""
    shared: dict[str, Any] = {
        "query": query,
        "claims": [],
        "seed_queries": [],
        "session_id": session_id,
    }
    await build_planner_flow().run_async(shared)
    return list(shared.get("claims") or []), list(shared.get("seed_queries") or [])
