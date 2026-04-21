"""Data access layer for UI components.

Decouples Mesop components from the new 5-agent pipeline shape.
"""

from __future__ import annotations

from a2a_research.a2a.cards import AGENT_CARDS
from a2a_research.models import (
    AgentRole,
    Claim,
    ResearchSession,
    default_roles,
)


def get_all_citations(session: ResearchSession) -> list[str]:
    """Deduplicated URL list (session.sources preserves first-seen order)."""
    seen: dict[str, None] = {}
    for source in session.sources:
        seen.setdefault(source.url, None)
    return list(seen.keys())


def get_verified_claims(session: ResearchSession) -> list[Claim]:
    """Verified claims — populated by the FactChecker via the coordinator."""
    return list(session.claims)


def get_agent_label(role: AgentRole) -> str:
    """Display label for an agent role (driven by the A2A AgentCard name)."""
    card = AGENT_CARDS.get(role)
    return card.name if card else role.value


def get_all_roles(session: ResearchSession | None = None) -> list[AgentRole]:
    """Return roles in pipeline order (session override falls back to defaults)."""
    if session and session.roles:
        return session.roles
    return default_roles()
