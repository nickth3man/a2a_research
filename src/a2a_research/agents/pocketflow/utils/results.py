"""Shared :class:`~a2a_research.models.AgentResult` construction helper."""

from __future__ import annotations

from a2a_research.models import AgentResult, AgentRole, AgentStatus, Claim


def create_agent_result(
    role: AgentRole,
    status: AgentStatus,
    message: str,
    raw_content: str = "",
    claims: list[Claim] | None = None,
    citations: list[str] | None = None,
) -> AgentResult:
    """Build an :class:`AgentResult` with defaulted list fields."""
    return AgentResult(
        role=role,
        status=status,
        message=message,
        raw_content=raw_content,
        claims=claims or [],
        citations=citations or [],
    )
