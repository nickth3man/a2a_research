"""Subjective golden query set data."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict

_GOLDEN_SET_SUBJECTIVE: list[EvalQuery] = [
    EvalQuery(
        id="SUBJ-001",
        text="What is the best smartphone for photography in 2026?",
        category="subjective",
        expected_claim_count=3,
        expected_citation_count=4,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="The best smartphone for photography depends on"
                " user priorities.",
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
            ExpectedVerdict(
                claim_text="Multiple flagship smartphones offer competitive"
                " camera systems in 2026.",
                verdict="SUPPORTED",
                min_evidence_count=2,
            ),
        ],
        notes="Opinion-driven; claims should be hedged and cite reviews.",
    ),
    EvalQuery(
        id="SUBJ-002",
        text="Is remote work better than office work for software engineers?",
        category="subjective",
        expected_claim_count=3,
        expected_citation_count=4,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="Remote work offers flexibility and reduced"
                " commuting.",
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
            ExpectedVerdict(
                claim_text=(
                    "Office work can improve spontaneous collaboration."
                ),
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
        ],
        notes="Balanced analysis expected; no single definitive claim.",
    ),
    EvalQuery(
        id="SUBJ-003",
        text="What is the greatest film ever made?",
        category="subjective",
        expected_claim_count=2,
        expected_citation_count=3,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="Greatest film is a subjective judgement with no"
                " universal consensus.",
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
        ],
        notes="Highly subjective; should acknowledge lack of consensus.",
    ),
    EvalQuery(
        id="SUBJ-004",
        text="Which programming language is best for beginners?",
        category="subjective",
        expected_claim_count=3,
        expected_citation_count=3,
        expected_verdicts=[
            ExpectedVerdict(
                claim_text="Python is often recommended for beginners due to"
                " readable syntax.",
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
            ExpectedVerdict(
                claim_text="The best language depends on the learner's goals.",
                verdict="SUPPORTED",
                min_evidence_count=1,
            ),
        ],
        notes="Opinion-driven; multiple reasonable answers exist.",
    ),
]
