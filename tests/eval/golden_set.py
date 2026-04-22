"""Golden query set models and accessors for evaluating the research
pipeline.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

__all__ = [
    "GOLDEN_SET",
    "EvalQuery",
    "get_by_category",
    "get_by_id",
]

QueryCategory = Literal[
    "factual", "subjective", "unanswerable", "sensitive", "ambiguous"
]


class ExpectedVerdict(BaseModel):
    """Expected claim-level verdict for a single claim derived from a query."""

    claim_text: str = Field(
        description="The expected claim text or a key phrase."
    )
    verdict: str = Field(
        description="Expected verdict: SUPPORTED, REFUTED, MIXED, etc."
    )
    min_evidence_count: int = Field(
        default=1,
        ge=0,
        description="Minimum number of evidence units expected.",
    )


class EvalQuery(BaseModel):
    """A single golden-set query with expected outcomes."""

    id: str = Field(description="Stable identifier, e.g. 'FACT-001'.")
    text: str = Field(
        description="The query string submitted to the pipeline."
    )
    category: QueryCategory = Field(description="Evaluation category.")
    expected_claim_count: int = Field(
        ge=0, description="Expected number of distinct claims in the output."
    )
    expected_citation_count: int = Field(
        ge=0,
        description="Expected number of unique citations / evidence units.",
    )
    expected_verdicts: list[ExpectedVerdict] = Field(
        default_factory=list,
        description="Expected verdicts for individual claims.",
    )
    notes: str = Field(
        default="", description="Human-readable evaluation notes."
    )


from tests.eval.golden_set_data import GOLDEN_SET  # noqa: E402


def get_by_category(category: QueryCategory) -> list[EvalQuery]:
    """Return all queries matching the given category."""
    return [q for q in GOLDEN_SET if q.category == category]


def get_by_id(query_id: str) -> EvalQuery | None:
    """Return a single query by its stable identifier, or None if not found."""
    for q in GOLDEN_SET:
        if q.id == query_id:
            return q
    return None
