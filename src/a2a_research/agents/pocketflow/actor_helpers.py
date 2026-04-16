"""Pure helpers for :class:`ActorNode` — payload construction and sender mapping.

Extracted from ``nodes.py`` to keep that module under the 200-line cap and to
make the A2A payload shape easy to test in isolation.
"""

from __future__ import annotations

from typing import Any

from a2a_research.models import AgentRole, ResearchSession

_SENDER_FOR_ROLE: dict[AgentRole, AgentRole] = {
    AgentRole.RESEARCHER: AgentRole.RESEARCHER,
    AgentRole.ANALYST: AgentRole.RESEARCHER,
    AgentRole.VERIFIER: AgentRole.ANALYST,
    AgentRole.PRESENTER: AgentRole.VERIFIER,
}


def get_sender_for_role(role: AgentRole) -> AgentRole:
    """Return the conventional upstream sender for a given recipient role."""
    return _SENDER_FOR_ROLE.get(role, role)


def build_payload(role: AgentRole, session: ResearchSession) -> dict[str, Any]:
    """Build the A2A message payload for a pipeline step."""
    if role == AgentRole.RESEARCHER:
        return {"query": session.query}
    if role == AgentRole.ANALYST:
        researcher = session.get_agent(AgentRole.RESEARCHER)
        return {
            "research_summary": researcher.raw_content,
            "citations": researcher.citations,
            "retrieved_chunks": [
                chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
            ],
        }
    if role == AgentRole.VERIFIER:
        analyst = session.get_agent(AgentRole.ANALYST)
        return {
            "claims": [c.model_dump() for c in analyst.claims],
            "query": session.query,
            "retrieved_chunks": [
                chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
            ],
        }
    if role == AgentRole.PRESENTER:
        verifier = session.get_agent(AgentRole.VERIFIER)
        return {"verified_claims": [c.model_dump() for c in verifier.claims]}
    return {}
