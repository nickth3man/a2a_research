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

import importlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from types import ModuleType

from a2a_research.models import AgentRole, ResearchSession

_ROLE_UTILS_PATH: dict[AgentRole, str] = {
    AgentRole.RESEARCHER: "a2a_research.agents.pocketflow.researcher.utils",
    AgentRole.ANALYST: "a2a_research.agents.pocketflow.analyst.utils",
    AgentRole.VERIFIER: "a2a_research.agents.pocketflow.verifier.utils",
    AgentRole.PRESENTER: "a2a_research.agents.pocketflow.presenter.utils",
}


def _get_agent_utils(role: AgentRole) -> ModuleType | None:
    path = _ROLE_UTILS_PATH.get(role)
    if path is None:
        return None
    return importlib.import_module(path)


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
