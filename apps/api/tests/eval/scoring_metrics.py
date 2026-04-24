"""Individual metric scoring functions for the evaluation harness."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tests.eval.golden_set import EvalQuery


def _normalize(text: str) -> str:
    """Lowercase and strip whitespace for fuzzy matching."""
    return text.lower().strip()


def _claim_matches(expected: str, actual: str, threshold: float = 0.6) -> bool:
    """Return True if ``actual`` contains enough words from ``expected``."""
    expected_words = set(_normalize(expected).split())
    actual_words = set(_normalize(actual).split())
    if not expected_words:
        return False
    overlap = len(expected_words & actual_words)
    return (overlap / len(expected_words)) >= threshold


def score_claim_recall(
    query: EvalQuery,
    actual_claims: list[str],
    threshold: float = 0.6,
) -> float:
    """Compute claim recall as the fraction of expected claims found."""
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
    """Compute citation accuracy as the fraction of citations that
    support claims."""
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
    """Compute independence score as the ratio of unique publishers."""
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
    """Compute adversary catch rate as the fraction of false claims caught."""
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
    """Compute a weighted composite score from the four primary metrics."""
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
