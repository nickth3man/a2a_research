"""Presenter role-specific helpers — A2A payload shape and upstream sender."""

from __future__ import annotations

from typing import Any

from a2a_research.models import AgentRole, ResearchSession

SENDER: AgentRole = AgentRole.VERIFIER


def build_payload(session: ResearchSession) -> dict[str, Any]:
    verifier = session.get_agent(AgentRole.VERIFIER)
    return {"verified_claims": [c.model_dump() for c in verifier.claims]}
