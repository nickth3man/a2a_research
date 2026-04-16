"""Researcher actor-node factory.

Returns a generic :class:`~a2a_research.agents.pocketflow.utils.nodes.ActorNode`
bound to :class:`~a2a_research.models.AgentRole.RESEARCHER`. The top-level
:mod:`a2a_research.agents.pocketflow.flow` composes these factories for the
full pipeline; this module exists so the Researcher can also be wired into a
single-agent :class:`~pocketflow.AsyncFlow` via ``researcher.flow``.
"""

from __future__ import annotations

from a2a_research.agents.pocketflow.utils.nodes import ActorNode
from a2a_research.models import AgentRole


def create_node(successor_role: AgentRole | None = None) -> ActorNode:
    return ActorNode(role=AgentRole.RESEARCHER, successor_role=successor_role)
