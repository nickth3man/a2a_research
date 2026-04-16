"""Data access layer for UI components.

This module decouples UI components from the agent pipeline structure by providing
data accessor functions that handle the details of which agents provide which data.
"""

from a2a_research.models import (
    AGENT_CARDS,
    AgentCard,
    AgentRole,
    Claim,
    ResearchSession,
)


def get_all_citations(session: ResearchSession) -> list[str]:
    """Aggregate all citations from researcher and verifier agents.

    Removes duplicates while preserving order.

    Args:
        session: The research session containing agent results.

    Returns:
        List of unique citation strings from all relevant agents.
    """
    researcher = session.get_agent(AgentRole.RESEARCHER)
    verifier = session.get_agent(AgentRole.VERIFIER)
    return list(dict.fromkeys(researcher.citations + verifier.citations))


def get_verified_claims(session: ResearchSession) -> list[Claim]:
    """Get verified claims from the verifier agent.

    Args:
        session: The research session containing agent results.

    Returns:
        List of claims from the verifier agent.
    """
    return session.get_agent(AgentRole.VERIFIER).claims


def get_agent_label(role: AgentRole) -> str:
    """Get the display label for an agent role.

    Looks up the label from AGENT_CARDS for a single source of truth.

    Args:
        role: The agent role to look up.

    Returns:
        The display name for the agent role.
    """
    card = AGENT_CARDS.get(role)
    return card.name if card else role.value


def get_all_roles() -> list[AgentRole]:
    """Get all agent roles in pipeline order.

    Returns:
        List of all agent roles from AGENT_CARDS.
    """
    return list(AGENT_CARDS.keys())
