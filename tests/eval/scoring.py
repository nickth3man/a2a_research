"""Scoring rubric for the research pipeline evaluation harness.

Provides pure functions that compute four metrics from a pipeline run
and an expected ground-truth query.

Metrics
-------
- **claim_recall**: Fraction of expected claims that were produced.
- **citation_accuracy**: Fraction of citations that actually support claims.
- **independence_score**: Ratio of independent publishers to total evidence.
- **adversary_catch_rate**: Fraction of false claims caught by the adversary.
- **composite_score**: Weighted combination of the four metrics.

All functions are deterministic and have no side effects, making them easy
to unit test.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

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


def _normalize(text: str) -> str:
    """Lowercase and strip whitespace for fuzzy matching."""
    return text.lower().strip()


def _claim_matches(expected: str, actual: str, threshold: float = 0.6) -> bool:
    """Return True if ``actual`` contains enough words from ``expected``.

    The heuristic requires at least ``threshold`` fraction of expected words
    to appear in the actual claim text.
    """
    expected_words = set(_normalize(expected).split())
    actual_words = set(_normalize(actual).split())
    if not expected_words:
        return False
    overlap = len(expected_words & actual_words)
    return (overlap / len(expected_words)) >= threshold


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


def score_claim_recall(
    query: EvalQuery,
    actual_claims: list[str],
    threshold: float = 0.6,
) -> float:
    """Compute claim recall as the fraction of expected claims found.

    Args:
        query: The ground-truth evaluation query.
        actual_claims: List of claim texts produced by the pipeline.
        threshold: Minimum word-overlap ratio for a fuzzy match.

    Returns:
        A float in ``[0.0, 1.0]``. Returns ``1.0`` when no claims are expected.
    """
    expected = query.expected_verdicts
    if not expected:
        return 1.0 if not actual_claims else 0.0

    remaining = list(actual_claims)
    matched = 0
    for ev in expected:
        for idx, ac in enumerate(remaining):
            if _claim_matches(ev.claim_text, ac, threshold):
                matched += 1
                remaining.pop(idx)
                break

    return matched / len(expected)


def score_citation_accuracy(
    actual_claims: list[str],
    actual_citations: list[str],
    supporting_citations: list[str] | None = None,
) -> float:
    """Compute citation accuracy as the fraction of citations that support claims.

    In the mock runner, ``supporting_citations`` can be provided explicitly.
    When None, the function assumes all citations are supporting (optimistic
    baseline), which yields ``1.0`` when citations exist.

    Args:
        actual_claims: Claims produced by the pipeline.
        actual_citations: Citations produced by the pipeline.
        supporting_citations: Optional subset of citations known to support claims.

    Returns:
        A float in ``[0.0, 1.0]``. Returns ``1.0`` when no citations are produced.
    """
    if not actual_citations:
        return 1.0 if not actual_claims else 0.0

    if supporting_citations is None:
        return 1.0

    supported = sum(1 for c in actual_citations if c in supporting_citations)
    return supported / len(actual_citations)


def score_independence(
    publisher_ids: list[str],
    syndication_clusters: list[list[str]] | None = None,
) -> float:
    """Compute independence score as the ratio of unique publishers.

    Collapses publishers that belong to the same syndication cluster into
    a single effective publisher.

    Args:
        publisher_ids: List of publisher identifiers for all evidence units.
        syndication_clusters: Optional list of clusters where each cluster is
            a list of publisher IDs that syndicate each other.

    Returns:
        A float in ``[0.0, 1.0]``. Returns ``0.0`` when no publishers are given.
    """
    if not publisher_ids:
        return 0.0

    unique = set(publisher_ids)
    if syndication_clusters:
        for cluster in syndication_clusters:
            cluster_set = set(cluster)
            overlap = unique & cluster_set
            if len(overlap) > 1:
                unique -= overlap
                unique.add(min(overlap))

    return len(unique) / len(publisher_ids)


def score_adversary_catch_rate(
    false_claims: list[str],
    caught_claims: list[str],
    threshold: float = 0.6,
) -> float:
    """Compute adversary catch rate as the fraction of false claims caught.

    Args:
        false_claims: List of claims that are known to be false or weak.
        caught_claims: List of claims that the adversary flagged.
        threshold: Minimum word-overlap ratio for a fuzzy match.

    Returns:
        A float in ``[0.0, 1.0]``. Returns ``1.0`` when there are no false claims.
    """
    if not false_claims:
        return 1.0

    caught = 0
    for fc in false_claims:
        if any(_claim_matches(fc, cc, threshold) for cc in caught_claims):
            caught += 1

    return caught / len(false_claims)


def compute_composite_score(
    claim_recall: float,
    citation_accuracy: float,
    independence_score: float,
    adversary_catch_rate: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Compute a weighted composite score from the four primary metrics.

    Default weights:
        - claim_recall: 0.35
        - citation_accuracy: 0.35
        - independence_score: 0.15
        - adversary_catch_rate: 0.15

    Args:
        claim_recall: Claim recall metric.
        citation_accuracy: Citation accuracy metric.
        independence_score: Independence score metric.
        adversary_catch_rate: Adversary catch rate metric.
        weights: Optional custom weights. Must sum to 1.0.

    Returns:
        A float in ``[0.0, 1.0]``.
    """
    default_weights = {
        "claim_recall": 0.35,
        "citation_accuracy": 0.35,
        "independence_score": 0.15,
        "adversary_catch_rate": 0.15,
    }
    w = default_weights if weights is None else weights

    total = sum(w.values())
    if total == 0:
        return 0.0

    score = (
        w.get("claim_recall", 0.0) * claim_recall
        + w.get("citation_accuracy", 0.0) * citation_accuracy
        + w.get("independence_score", 0.0) * independence_score
        + w.get("adversary_catch_rate", 0.0) * adversary_catch_rate
    )
    return score / total


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
    """Run the full scoring rubric against a single query result.

    This is a convenience wrapper that calls each metric function and
    returns an :class:`EvalScores` container.

    Args:
        query: Ground-truth evaluation query.
        actual_claims: Claims produced by the pipeline.
        actual_citations: Citations produced by the pipeline.
        publisher_ids: Publisher identifiers for evidence units.
        false_claims: Claims known to be false (for adversary scoring).
        caught_claims: Claims flagged by the adversary.
        supporting_citations: Subset of citations that actually support claims.
        syndication_clusters: Optional syndication cluster definitions.

    Returns:
        Populated :class:`EvalScores` instance.
    """
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
