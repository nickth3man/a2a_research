"""Mock pipeline runner for regression evaluation."""

from __future__ import annotations

from typing import Any

from tests.eval.golden_set import EvalQuery


def _mock_run_pipeline(query: EvalQuery) -> dict[str, Any]:
    """Mock pipeline runner that returns deterministic synthetic results."""
    category = query.category
    if category == "factual":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/cite{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 3}" for i in range(len(actual_citations))
        ]
        false_claims: list[str] = []
        caught_claims: list[str] = []
    elif category == "subjective":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/review{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 4}" for i in range(len(actual_citations))
        ]
        false_claims = []
        caught_claims = []
    elif category == "unanswerable":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []
    elif category == "sensitive":
        actual_claims = []
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []
    elif category == "ambiguous":
        actual_claims = [ev.claim_text for ev in query.expected_verdicts]
        actual_citations = [
            f"https://example.com/sense{i}"
            for i in range(query.expected_citation_count)
        ]
        publisher_ids = [
            f"publisher_{i % 3}" for i in range(len(actual_citations))
        ]
        false_claims = []
        caught_claims = []
    else:
        actual_claims = []
        actual_citations = []
        publisher_ids = []
        false_claims = []
        caught_claims = []

    return {
        "actual_claims": actual_claims,
        "actual_citations": actual_citations,
        "publisher_ids": publisher_ids,
        "false_claims": false_claims,
        "caught_claims": caught_claims,
        "supporting_citations": actual_citations,
    }
