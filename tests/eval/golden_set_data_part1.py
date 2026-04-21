"""Golden query set data (part 1: factual, subjective, unanswerable)."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict

_GOLDEN_SET_PART1: list[EvalQuery] = [
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
