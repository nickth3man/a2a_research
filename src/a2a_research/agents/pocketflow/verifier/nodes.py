"""Verifier actor-node factory.

Returns a generic :class:`~a2a_research.agents.pocketflow.utils.nodes.ActorNode`
bound to :class:`~a2a_research.models.AgentRole.VERIFIER`.
"""

from __future__ import annotations

from a2a_research.agents.pocketflow.utils.nodes import ActorNode
from a2a_research.models import AgentRole


def create_node(successor_role: AgentRole | None = None) -> ActorNode:
    return ActorNode(role=AgentRole.VERIFIER, successor_role=successor_role)
