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
    from a2a_research.models import Claim, ClaimDAG

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


async def plan(
    query: str,
    *,
    session_id: str = "",
    include_dag: bool = False,
) -> tuple[list[Claim], list[str]] | tuple[list[Claim], ClaimDAG, list[str]]:
    """Run the Planner flow.

    Returns ``(claims, seed_queries)`` by default for backward compatibility.
    Set ``include_dag=True`` to receive ``(claims, claim_dag, seed_queries)``.
    """
    shared: dict[str, Any] = {
        "query": query,
        "claims": [],
        "claim_dag": None,
        "seed_queries": [],
        "session_id": session_id,
    }
    await build_planner_flow().run_async(shared)
    claims = list(shared.get("claims") or [])
    claim_dag = shared.get("claim_dag")
    seed_queries = list(shared.get("seed_queries") or [])
    if include_dag:
        return claims, claim_dag, seed_queries
    return claims, seed_queries
