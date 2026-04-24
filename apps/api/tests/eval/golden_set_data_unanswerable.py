"""Unanswerable golden query set data."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict

_GOLDEN_SET_UNANSWERABLE: list[EvalQuery] = [
    EvalQuery(
        id="UNAN-001",
        text="What did Napoleon think about quantum physics?",
        category="unanswerable",
        expected_claim_count=0,
        expected_citation_count=0,
        expected_verdicts=[],
        notes="Anachronistic; quantum physics emerged after Napoleon's death.",
    ),
    EvalQuery(
        id="UNAN-002",
        text="What is the exact population of Earth at this exact second?",
        category="unanswerable",
        expected_claim_count=0,
        expected_citation_count=0,
        expected_verdicts=[],
        notes="Impossible to know in real time.",
    ),
    EvalQuery(
        id="UNAN-003",
        text="What are the winning lottery numbers for next week?",
        category="unanswerable",
        expected_claim_count=0,
        expected_citation_count=0,
        expected_verdicts=[],
        notes="Future event; no evidence available.",
    ),
    EvalQuery(
        id="UNAN-004",
        text="What is inside a black hole beyond the event horizon?",
        category="unanswerable",
        expected_claim_count=1,
        expected_citation_count=2,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="Information about the interior of a black hole"
                " beyond the event horizon is currently inaccessible to"
                " observation.",
                verdict="INSUFFICIENT_EVIDENCE",
                min_evidence_count=1,
            ),
        ],
        notes="Beyond current observational capability.",
    ),
]
