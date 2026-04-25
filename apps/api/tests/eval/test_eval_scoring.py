"""Tests for scoring functions in the evaluation harness."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery, ExpectedVerdict
from tests.eval.scoring_metrics import (
    score_citation_accuracy,
    score_claim_recall,
    score_independence,
)


class TestScoringClaimRecall:
    def test_perfect_recall(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Paris is the capital of France.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["Paris is the capital of France."]
        assert score_claim_recall(q, actual) == 1.0

    def test_partial_recall(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=2,
            expected_citation_count=2,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Paris is the capital of France.",
                    verdict="SUPPORTED",
                ),
                ExpectedVerdict(
                    claim_text="Berlin is the capital of Germany.",
                    verdict="SUPPORTED",
                ),
            ],
        )
        actual = ["Paris is the capital of France."]
        assert score_claim_recall(q, actual) == 0.5

    def test_zero_expected_claims_with_none_actual(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="sensitive",
            expected_claim_count=0,
            expected_citation_count=0,
            expected_verdicts=[],
        )
        assert score_claim_recall(q, []) == 1.0

    def test_zero_expected_claims_with_some_actual(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="sensitive",
            expected_claim_count=0,
            expected_citation_count=0,
            expected_verdicts=[],
        )
        assert score_claim_recall(q, ["unexpected claim"]) == 0.0

    def test_fuzzy_match_threshold(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="The quick brown fox jumps over the lazy dog.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["The quick brown fox jumps over the lazy dog."]
        assert score_claim_recall(q, actual, threshold=0.9) == 1.0

    def test_fuzzy_match_fails_below_threshold(self) -> None:
        q = EvalQuery(
            id="T",
            text="t",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[
                ExpectedVerdict(
                    claim_text="Completely different sentence about nothing"
                    " similar.",
                    verdict="SUPPORTED",
                )
            ],
        )
        actual = ["This is an unrelated claim."]
        assert score_claim_recall(q, actual) == 0.0


class TestScoringCitationAccuracy:
    def test_all_supporting(self) -> None:
        assert (
            score_citation_accuracy(
                ["c1"], ["a", "b"], supporting_citations=["a", "b"]
            )
            == 1.0
        )

    def test_half_supporting(self) -> None:
        assert (
            score_citation_accuracy(
                ["c1"], ["a", "b"], supporting_citations=["a"]
            )
            == 0.5
        )

    def test_no_citations(self) -> None:
        assert score_citation_accuracy(["c1"], []) == 0.0

    def test_no_citations_no_claims(self) -> None:
        assert score_citation_accuracy([], []) == 1.0

    def test_none_supporting_citations(self) -> None:
        assert score_citation_accuracy(["c1"], ["a", "b"]) == 1.0


class TestScoringIndependence:
    def test_all_unique(self) -> None:
        assert score_independence(["a", "b", "c"]) == 1.0

    def test_some_duplicates(self) -> None:
        assert score_independence(["a", "a", "b"]) == 2 / 3

    def test_empty(self) -> None:
        assert score_independence([]) == 0.0

    def test_with_syndication_clusters(self) -> None:
        publishers = ["a", "b", "c", "d"]
        clusters = [["a", "b"]]
        result = score_independence(publishers, clusters)
        assert result == 3 / 4

    def test_cluster_with_no_overlap(self) -> None:
        publishers = ["a", "b"]
        clusters = [["c", "d"]]
        assert score_independence(publishers, clusters) == 1.0
