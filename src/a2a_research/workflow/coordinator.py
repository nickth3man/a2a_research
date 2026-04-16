"""Async coordinator — builds a linear ``AsyncFlow`` over four :class:`~a2a_research.workflow.nodes.ActorNode` instances.

Used by higher-level builders; ``run_coordinator`` is a convenience that runs the flow
with a fresh ``shared`` dict seeded with ``session`` and ``messages``.
"""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncFlow

from ..models import AgentRole, ResearchSession
from .nodes import create_actor_node


def build_coordinator() -> AsyncFlow[Any, Any]:
    researcher = create_actor_node(AgentRole.RESEARCHER, AgentRole.ANALYST)
    analyst = create_actor_node(AgentRole.ANALYST, AgentRole.VERIFIER)
    verifier = create_actor_node(AgentRole.VERIFIER, AgentRole.PRESENTER)
    presenter = create_actor_node(AgentRole.PRESENTER, None)

    _ = researcher >> analyst >> verifier >> presenter

    flow: AsyncFlow[Any, Any] = AsyncFlow(start=researcher)
    return flow


async def run_coordinator(session: ResearchSession) -> ResearchSession:
    shared: dict[str, Any] = {
        "session": session,
        "messages": [],
        "current_agent": None,
    }

    flow = build_coordinator()
    await flow.run_async(shared)

    return shared["session"]
