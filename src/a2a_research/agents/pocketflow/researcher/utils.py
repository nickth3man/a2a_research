"""Researcher role-specific helpers — A2A payload shape and upstream sender."""

from __future__ import annotations

from typing import Any

from a2a_research.models import AgentRole, ResearchSession

SENDER: AgentRole = AgentRole.RESEARCHER


def build_payload(session: ResearchSession) -> dict[str, Any]:
    return {"query": session.query}
