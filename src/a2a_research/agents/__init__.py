"""Agent implementations for the 4-agent research pipeline.

Re-exports the public PocketFlow runtime API from
:mod:`a2a_research.agents.pocketflow` so downstream code can say
``from a2a_research.agents import researcher_invoke`` without caring whether an
agent lives in its own subpackage or is composed through PocketFlow.

Order: Researcher → Analyst → Verifier → Presenter. Each step:

- Reads the shared :class:`~a2a_research.models.ResearchSession` and prior outputs.
- Calls the LLM (or deterministic fallback on
  :class:`~a2a_research.providers.ProviderRequestError`).
- Writes its :class:`~a2a_research.models.AgentResult` back into ``session.agent_results``.
"""

from __future__ import annotations

from a2a_research.agents.pocketflow import (
    AgentRegistry,
    AgentSpec,
    analyst_invoke,
    get_agent_handler,
    get_agent_spec,
    get_registry,
    parse_claims_from_analyst,
    parse_verified_claims,
    presenter_invoke,
    register_agent,
    researcher_invoke,
    run_research_sync,
    verifier_invoke,
)

__all__ = [
    "AgentRegistry",
    "AgentSpec",
    "analyst_invoke",
    "get_agent_handler",
    "get_agent_spec",
    "get_registry",
    "parse_claims_from_analyst",
    "parse_verified_claims",
    "presenter_invoke",
    "register_agent",
    "researcher_invoke",
    "run_research_sync",
    "verifier_invoke",
]
