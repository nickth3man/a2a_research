"""Tests for NoveltyTracker."""

from __future__ import annotations

from core import NoveltyTracker


class TestNoveltyTracker:
    def test_defaults(self):
        nt = NoveltyTracker()
        assert nt.marginal_gain == 0

    def test_marginal_gain_calculation(self):
        nt = NoveltyTracker(
            new_unique_hits=1,
            new_unique_pages=1,
            new_supporting_evidence_spans=1,
            new_independent_publishers=1,
        )
        assert nt.marginal_gain == 1 + 1 + 1 + 2

    def test_marginal_gain_weights_publishers_double(self):
        nt = NoveltyTracker(new_independent_publishers=3)
        assert nt.marginal_gain == 6

    def test_marginal_gain_zero_publishers(self):
        nt = NoveltyTracker(
            new_unique_hits=5,
            new_unique_pages=3,
            new_supporting_evidence_spans=2,
        )
        assert nt.marginal_gain == 10

    def test_marginal_gain_all_zero(self):
        nt = NoveltyTracker(
            new_unique_hits=0,
            new_unique_pages=0,
            new_supporting_evidence_spans=0,
            new_independent_publishers=0,
        )
        assert nt.marginal_gain == 0
