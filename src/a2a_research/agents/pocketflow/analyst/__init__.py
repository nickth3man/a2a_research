"""Analyst subpackage — registers the Analyst handler on import."""

from __future__ import annotations

from a2a_research.agents.pocketflow.registry import register_agent
from a2a_research.models import AgentRole

from .agent import analyst_invoke, parse_claims_from_analyst

register_agent(
    AgentRole.ANALYST,
    name="Analyst",
    description="Decomposes the query into atomic verifiable claims.",
)(analyst_invoke)

__all__ = ["analyst_invoke", "parse_claims_from_analyst"]
