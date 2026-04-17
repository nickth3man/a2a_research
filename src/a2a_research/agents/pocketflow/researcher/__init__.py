"""Researcher subpackage — registers the Researcher handler on import."""

from __future__ import annotations

from a2a_research.agents.pocketflow.utils.registry import register_agent
from a2a_research.models import AgentRole

from .main import researcher_invoke

register_agent(
    AgentRole.RESEARCHER,
    name="Researcher",
    description="Retrieves and ranks RAG corpus chunks for a research query.",
)(researcher_invoke)

__all__ = ["researcher_invoke"]
