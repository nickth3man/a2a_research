"""State for the FactChecker langgraph.

Accumulates evidence and per-round search/fetch work lists. ``round`` starts
at 0 and is incremented by the verify_node after each verification pass.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

# LangGraph resolves TypedDict field annotations at runtime via get_type_hints,
# so these imports must remain at module scope (not under TYPE_CHECKING).
from a2a_research.models import Claim, WebSource  # noqa: TC001
from a2a_research.tools import PageContent, WebHit  # noqa: TC001

__all__ = ["FactCheckRunResult", "FactCheckState"]


class FactCheckRunResult(TypedDict):
    verified_claims: list[Claim]
    sources: list[WebSource]
    errors: list[str]
    search_exhausted: bool
    rounds: int


class FactCheckState(TypedDict, total=False):
    session_id: str
    query: str
    claims: list[Claim]
    evidence: Annotated[list[PageContent], operator.add]
    hits: Annotated[list[WebHit], operator.add]
    sources: Annotated[list[WebSource], operator.add]
    errors: Annotated[list[str], operator.add]
    round: int
    max_rounds: int
    pending_queries: list[str]
    pending_urls: list[str]
    search_exhausted: bool
