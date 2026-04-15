"""Async coordinator — an AsyncFlow that orchestrates the 4-agent pipeline."""

from __future__ import annotations

from typing import Any

from pocketflow_reference.pocketflow_source import AsyncFlow

from ..models import AgentRole, ResearchSession
from .nodes import create_actor_node


def build_coordinator() -> AsyncFlow:
    researcher = create_actor_node(AgentRole.RESEARCHER, AgentRole.ANALYST)
    analyst = create_actor_node(AgentRole.ANALYST, AgentRole.VERIFIER)
    verifier = create_actor_node(AgentRole.VERIFIER, AgentRole.PRESENTER)
    presenter = create_actor_node(AgentRole.PRESENTER, None)

    _ = researcher >> analyst >> verifier >> presenter

    flow = AsyncFlow(start=researcher)
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
