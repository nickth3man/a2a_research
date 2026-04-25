"""PocketFlow AsyncFlow wiring for the Clarifier."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncFlow

from agents.pocketflow.clarifier.nodes import (
    AuditNode,
    CommitNode,
    DisambiguateNode,
    TerminalNode,
)

__all__ = ["build_clarifier_flow", "clarify"]


def build_clarifier_flow() -> AsyncFlow[Any, Any]:
    disambiguate = DisambiguateNode()
    commit = CommitNode()
    audit = AuditNode()
    terminal = TerminalNode()

    _ = disambiguate - "default" >> commit
    _ = commit - "default" >> audit
    _ = audit - "default" >> terminal

    return AsyncFlow(start=disambiguate)


async def clarify(
    query: str, query_class: str = "factual", *, session_id: str = ""
) -> dict[str, Any]:
    """Run the Clarifier flow and return the clarification result."""
    shared: dict[str, Any] = {
        "query": query,
        "query_class": query_class,
        "session_id": session_id,
        "disambiguations": [],
        "committed_interpretation": "",
        "audit_note": "",
    }
    await build_clarifier_flow().run_async(shared)
    return {
        "disambiguations": list(shared.get("disambiguations") or []),
        "committed_interpretation": str(
            shared.get("committed_interpretation") or query
        ),
        "audit_note": str(shared.get("audit_note") or ""),
    }
