"""Dispatcher for :class:`ActorNode` — delegates payload/sender lookup to each
agent's own ``utils`` module (``researcher.utils``, ``analyst.utils`` etc.).

Each agent owns the shape of the A2A payload it expects and the conventional
upstream sender. This dispatcher is the single point that maps an
:class:`~a2a_research.models.AgentRole` to the right agent module, so the
generic :class:`~a2a_research.agents.pocketflow.utils.nodes.ActorNode` stays
role-agnostic.

Imports are lazy to avoid partial-init cycles during package bootstrap: each
agent subpackage is registered at import time via ``register_agent``, and the
generic ``ActorNode`` base is loaded alongside the agent subpackages.
"""

from __future__ import annotations

from types import ModuleType
from typing import Any

from a2a_research.models import AgentRole, ResearchSession


def _get_agent_utils(role: AgentRole) -> ModuleType | None:
    if role == AgentRole.RESEARCHER:
        from ..researcher import utils as agent_utils
    elif role == AgentRole.ANALYST:
        from ..analyst import utils as agent_utils
    elif role == AgentRole.VERIFIER:
        from ..verifier import utils as agent_utils
    elif role == AgentRole.PRESENTER:
        from ..presenter import utils as agent_utils
    else:
        return None
    return agent_utils


def get_sender_for_role(role: AgentRole) -> AgentRole:
    """Return the conventional upstream sender for a given recipient role."""
    agent_utils = _get_agent_utils(role)
    sender = getattr(agent_utils, "SENDER", None) if agent_utils is not None else None
    return sender if isinstance(sender, AgentRole) else role


def build_payload(role: AgentRole, session: ResearchSession) -> dict[str, Any]:
    """Build the A2A message payload for a pipeline step."""
    agent_utils = _get_agent_utils(role)
    if agent_utils is None:
        return {}
    return agent_utils.build_payload(session)
