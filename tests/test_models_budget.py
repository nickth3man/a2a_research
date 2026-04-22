"""Tests for BudgetConsumption, NoveltyTracker, and WorkflowBudget."""

from __future__ import annotations

from a2a_research.models import (
    BudgetConsumption,
    NoveltyTracker,
    WorkflowBudget,
)


class TestBudgetConsumption:
    def test_defaults(self):
        bc = BudgetConsumption()
        assert bc.rounds == 0
        assert bc.tokens_consumed == 0
        assert bc.wall_seconds == 0.0
        assert bc.http_calls == 0
        assert bc.urls_fetched == 0
        assert bc.critic_revision_loops == 0

    def test_not_exhausted(self):
        bc = BudgetConsumption()
        budget = WorkflowBudget()
        assert bc.is_exhausted(budget) is False

    def test_exhausted_by_rounds(self):
        bc = BudgetConsumption(rounds=5)
        budget = WorkflowBudget(max_rounds=5)
        assert bc.is_exhausted(budget) is True

    def test_exhausted_by_tokens(self):
        bc = BudgetConsumption(tokens_consumed=200000)
        budget = WorkflowBudget(max_tokens=200000)
        assert bc.is_exhausted(budget) is True

    def test_exhausted_by_wall_seconds(self):
        bc = BudgetConsumption(wall_seconds=180.0)
        budget = WorkflowBudget(max_wall_seconds=180.0)
        assert bc.is_exhausted(budget) is True

    def test_exhausted_by_http_calls(self):
        bc = BudgetConsumption(http_calls=50)
        budget = WorkflowBudget(max_http_calls=50)
        assert bc.is_exhausted(budget) is True

    def test_exhausted_by_critic_loops(self):
        bc = BudgetConsumption(critic_revision_loops=2)
        budget = WorkflowBudget(max_critic_revision_loops=2)
        assert bc.is_exhausted(budget) is True

    def test_not_exhausted_below_threshold(self):
        bc = BudgetConsumption(
            rounds=4, tokens_consumed=100000, wall_seconds=100.0
        )
        budget = WorkflowBudget()
        assert bc.is_exhausted(budget) is False

    def test_any_dimension_exhausts(self):
        budget = WorkflowBudget(
            max_rounds=10,
            max_tokens=1000000,
            max_wall_seconds=600,
            max_http_calls=100,
            max_critic_revision_loops=5,
        )
        assert BudgetConsumption(rounds=10).is_exhausted(budget)
        assert BudgetConsumption(tokens_consumed=1000000).is_exhausted(budget)
        assert BudgetConsumption(wall_seconds=600.0).is_exhausted(budget)
        assert BudgetConsumption(http_calls=100).is_exhausted(budget)
        assert BudgetConsumption(critic_revision_loops=5).is_exhausted(budget)


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


class TestWorkflowBudget:
    def test_defaults(self):
        b = WorkflowBudget()
        assert b.max_rounds == 5
        assert b.max_tokens == 200000
        assert b.max_wall_seconds == 180.0
        assert b.max_http_calls == 50
        assert b.max_urls_fetched == 20
        assert b.min_marginal_evidence == 2
        assert b.max_critic_revision_loops == 2

    def test_custom(self):
        b = WorkflowBudget(max_rounds=10, max_tokens=500000)
        assert b.max_rounds == 10
        assert b.max_tokens == 500000
