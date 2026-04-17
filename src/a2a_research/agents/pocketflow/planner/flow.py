"""PocketFlow AsyncFlow wiring for the Planner.

``DecomposeNode`` emits either ``default`` (LLM succeeded, claims extracted)
or ``fallback`` (degrade to a single claim containing the raw query) so the
downstream pipeline always sees at least one claim.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pocketflow import AsyncFlow

from a2a_research.agents.pocketflow.planner.nodes import (
    DecomposeNode,
    FallbackNode,
    TerminalNode,
)

if TYPE_CHECKING:
    from a2a_research.models import Claim

__all__ = ["build_planner_flow", "plan"]


def build_planner_flow() -> AsyncFlow[Any, Any]:
    decompose = DecomposeNode()
    fallback = FallbackNode()
    terminal = TerminalNode()
    _ = decompose - "default" >> terminal
    _ = decompose - "fallback" >> fallback
    flow: AsyncFlow[Any, Any] = AsyncFlow(start=decompose)
    return flow


async def plan(query: str) -> tuple[list[Claim], list[str]]:
    """Run the Planner flow and return (claims, seed_queries)."""
    shared: dict[str, Any] = {"query": query, "claims": [], "seed_queries": []}
    await build_planner_flow().run_async(shared)
    return list(shared.get("claims") or []), list(shared.get("seed_queries") or [])
