"""Builder — constructs the PocketFlow workflow graph declaratively."""

from __future__ import annotations

from typing import Any

from pocketflow import AsyncFlow

from ..models import AgentRole
from .nodes import ActorNode, create_actor_node


def build_workflow(
    roles: list[AgentRole] | None = None,
) -> tuple[AsyncFlow, dict[str, Any]]:
    if roles is None:
        roles = [
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.VERIFIER,
            AgentRole.PRESENTER,
        ]

    nodes: dict[AgentRole, ActorNode] = {}
    for role in roles:
        nodes[role] = create_actor_node(role)

    for i, role in enumerate(roles[:-1]):
        _ = nodes[role] >> nodes[roles[i + 1]]

    start = nodes[roles[0]]
    flow = AsyncFlow(start=start)

    shared: dict[str, Any] = {
        "session": None,
        "messages": [],
        "current_agent": None,
    }

    return flow, shared


def get_workflow() -> tuple[AsyncFlow, dict[str, Any]]:
    return build_workflow()
