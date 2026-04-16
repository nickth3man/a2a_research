"""Analyst role-specific helpers — A2A payload shape and upstream sender."""

from __future__ import annotations

from typing import Any

from a2a_research.models import AgentRole, ResearchSession

SENDER: AgentRole = AgentRole.RESEARCHER


def build_payload(session: ResearchSession) -> dict[str, Any]:
    researcher = session.get_agent(AgentRole.RESEARCHER)
    return {
        "research_summary": researcher.raw_content,
        "citations": researcher.citations,
        "retrieved_chunks": [
            chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
        ],
    }
