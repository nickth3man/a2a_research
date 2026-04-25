"""Static AgentCard for the FactChecker HTTP service."""

from __future__ import annotations

from core import AgentRole, get_card

FACT_CHECKER_CARD = get_card(AgentRole.FACT_CHECKER)

__all__ = ["FACT_CHECKER_CARD"]
