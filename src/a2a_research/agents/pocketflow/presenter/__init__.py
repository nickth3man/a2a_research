"""Presenter subpackage — registers the Presenter handler on import."""

from __future__ import annotations

from a2a_research.agents.pocketflow.registry import register_agent
from a2a_research.models import AgentRole

from .agent import presenter_invoke

register_agent(
    AgentRole.PRESENTER,
    name="Presenter",
    description="Synthesises verified claims into a markdown research report.",
)(presenter_invoke)

__all__ = ["presenter_invoke"]
