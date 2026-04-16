"""Verifier subpackage — registers the Verifier handler on import."""

from __future__ import annotations

from a2a_research.agents.pocketflow.registry import register_agent
from a2a_research.models import AgentRole

from .agent import verifier_invoke
from .parsers import parse_verified_claims

register_agent(
    AgentRole.VERIFIER,
    name="Verifier",
    description="Verifies atomic claims against retrieved evidence.",
)(verifier_invoke)

__all__ = ["parse_verified_claims", "verifier_invoke"]
