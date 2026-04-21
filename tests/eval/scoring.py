"""Scoring rubric for the research pipeline evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tests.eval.scoring_metrics import (
    compute_composite_score,
    score_adversary_catch_rate,
    score_citation_accuracy,
    score_claim_recall,
    score_independence,
)

if TYPE_CHECKING:
    from tests.eval.golden_set import EvalQuery

__all__ = [
    "EvalScores",
    "compute_composite_score",
    "score_adversary_catch_rate",
    "score_citation_accuracy",
    "score_claim_recall",
    "score_independence",
    "score_run",
]


@dataclass(frozen=True, slots=True)
class EvalScores:
    """Container for all evaluation metrics for a single query run."""

    claim_recall: float
    citation_accuracy: float
    independence_score: float
    adversary_catch_rate: float
    composite_score: float

    def to_dict(self) -> dict[str, float]:
        """Return a plain dictionary representation."""
        return {
            "claim_recall": self.claim_recall,
            "citation_accuracy": self.citation_accuracy,
            "independence_score": self.independence_score,
            "adversary_catch_rate": self.adversary_catch_rate,
            "composite_score": self.composite_score,
        }


def score_run(
    query: EvalQuery,
    actual_claims: list[str],
    actual_citations: list[str] | None = None,
    publisher_ids: list[str] | None = None,
    false_claims: list[str] | None = None,
    caught_claims: list[str] | None = None,
    supporting_citations: list[str] | None = None,
    syndication_clusters: list[list[str]] | None = None,
) -> EvalScores:
    """Run the full scoring rubric against a single query result."""
    actual_citations = actual_citations or []
    publisher_ids = publisher_ids or []
    false_claims = false_claims or []
    caught_claims = caught_claims or []

    claim_recall = score_claim_recall(query, actual_claims)
    citation_accuracy = score_citation_accuracy(
        actual_claims, actual_citations, supporting_citations
    )
    independence_score = score_independence(
        publisher_ids, syndication_clusters
    )
    adversary_catch_rate = score_adversary_catch_rate(
        false_claims, caught_claims
    )
    composite_score = compute_composite_score(
        claim_recall,
        citation_accuracy,
        independence_score,
        adversary_catch_rate,
    )

    return EvalScores(
        claim_recall=claim_recall,
        citation_accuracy=citation_accuracy,
        independence_score=independence_score,
        adversary_catch_rate=adversary_catch_rate,
        composite_score=composite_score,
    )
