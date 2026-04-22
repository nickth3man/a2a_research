"""Tests for the evaluation harness golden set."""

from __future__ import annotations

from tests.eval.golden_set import (
    GOLDEN_SET,
    EvalQuery,
    ExpectedVerdict,
    get_by_category,
    get_by_id,
)


class TestGoldenSet:
    def test_golden_set_has_20_queries(self) -> None:
        assert len(GOLDEN_SET) == 20

    def test_all_ids_are_unique(self) -> None:
        ids = [q.id for q in GOLDEN_SET]
        assert len(ids) == len(set(ids))

    def test_categories_distribution(self) -> None:
        counts: dict[str, int] = {}
        for q in GOLDEN_SET:
            counts[q.category] = counts.get(q.category, 0) + 1
        assert counts.get("factual", 0) == 4
        assert counts.get("subjective", 0) == 4
        assert counts.get("unanswerable", 0) == 4
        assert counts.get("sensitive", 0) == 4
        assert counts.get("ambiguous", 0) == 4

    def test_get_by_category_factual(self) -> None:
        factual = get_by_category("factual")
        assert len(factual) == 4
        assert all(q.category == "factual" for q in factual)

    def test_get_by_category_empty_for_unknown(self) -> None:
        assert get_by_category("nonexistent") == []  # type: ignore[arg-type]

    def test_get_by_id_found(self) -> None:
        q = get_by_id("FACT-001")
        assert q is not None
        assert q.text == "What is the capital of France?"

    def test_get_by_id_not_found(self) -> None:
        assert get_by_id("UNKNOWN") is None

    def test_eval_query_model(self) -> None:
        ev = ExpectedVerdict(
            claim_text="test", verdict="SUPPORTED", min_evidence_count=1
        )
        q = EvalQuery(
            id="TEST-001",
            text="Test query",
            category="factual",
            expected_claim_count=1,
            expected_citation_count=1,
            expected_verdicts=[ev],
            notes="note",
        )
        assert q.id == "TEST-001"
        assert q.category == "factual"
        assert len(q.expected_verdicts) == 1
