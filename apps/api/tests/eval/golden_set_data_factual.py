"""Factual golden query set data."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict

_GOLDEN_SET_FACTUAL: list[EvalQuery] = [
    EvalQuery(
        id="FACT-001",
        text="What is the capital of France?",
        category="factual",
        expected_claim_count=1,
        expected_citation_count=2,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="The capital of France is Paris.",
                verdict="SUPPORTED",
                min_evidence_count=2,
            ),
        ],
        notes="Basic geography; should be supported by encyclopedic sources.",
    ),
    EvalQuery(
        id="FACT-002",
        text="What is the atomic number of gold?",
        category="factual",
        expected_claim_count=1,
        expected_citation_count=2,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="The atomic number of gold is 79.",
                verdict="SUPPORTED",
                min_evidence_count=2,
            ),
        ],
        notes="Chemistry fact; widely documented.",
    ),
    EvalQuery(
        id="FACT-003",
        text="Who wrote 'To Kill a Mockingbird'?",
        category="factual",
        expected_claim_count=1,
        expected_citation_count=2,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="Harper Lee wrote 'To Kill a Mockingbird'.",
                verdict="SUPPORTED",
                min_evidence_count=2,
            ),
        ],
        notes="Literature fact; no ambiguity.",
    ),
    EvalQuery(
        id="FACT-004",
        text="What year did the Berlin Wall fall?",
        category="factual",
        expected_claim_count=1,
        expected_citation_count=2,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="The Berlin Wall fell in 1989.",
                verdict="SUPPORTED",
                min_evidence_count=2,
            ),
        ],
        notes="Historical fact; November 9, 1989.",
    ),
]
