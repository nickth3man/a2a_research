"""Tests for BudgetConsumption, NoveltyTracker integration, and per-stage
timeouts."""

from __future__ import annotations

from unittest.mock import MagicMock

from core.models import (
    AgentRole,
    BudgetConsumption,
    NoveltyTracker,
    WorkflowBudget,
)
from workflow.workflow_engine import (
    _PER_STAGE_TIMEOUTS,
    _budget_from_settings,
    _stage_timeout,
)

# ── BudgetConsumption unit tests
# ──────────────────────────────────────────────


class TestBudgetConsumption:
    def test_initial_state_not_exhausted(self):
        bc = BudgetConsumption()
        budget = WorkflowBudget()
        assert not bc.is_exhausted(budget)

    def test_rounds_exhausted(self):
        bc = BudgetConsumption(rounds=5)
        budget = WorkflowBudget(max_rounds=5)
        assert bc.is_exhausted(budget)

    def test_tokens_exhausted(self):
        bc = BudgetConsumption(tokens_consumed=200_000)
        budget = WorkflowBudget(max_tokens=200_000)
        assert bc.is_exhausted(budget)

    def test_wall_seconds_exhausted(self):
        bc = BudgetConsumption(wall_seconds=180.0)
        budget = WorkflowBudget(max_wall_seconds=180.0)
        assert bc.is_exhausted(budget)

    def test_http_calls_exhausted(self):
        bc = BudgetConsumption(http_calls=50)
        budget = WorkflowBudget(max_http_calls=50)
        assert bc.is_exhausted(budget)

    def test_critic_loops_exhausted(self):
        bc = BudgetConsumption(critic_revision_loops=2)
        budget = WorkflowBudget(max_critic_revision_loops=2)
        assert bc.is_exhausted(budget)

    def test_partial_exhaustion(self):
        bc = BudgetConsumption(rounds=3, http_calls=50)
        budget = WorkflowBudget(max_rounds=5, max_http_calls=50)
        assert bc.is_exhausted(budget)

    def test_not_exhausted_below_limits(self):
        bc = BudgetConsumption(
            rounds=4, tokens_consumed=100_000, wall_seconds=100.0
        )
        budget = WorkflowBudget(
            max_rounds=5, max_tokens=200_000, max_wall_seconds=180.0
        )
        assert not bc.is_exhausted(budget)


# ── NoveltyTracker unit tests
# ─────────────────────────────────────────────────


class TestNoveltyTracker:
    def test_initial_marginal_gain_zero(self):
        nt = NoveltyTracker()
        assert nt.marginal_gain == 0

    def test_marginal_gain_calculation(self):
        nt = NoveltyTracker(
            new_unique_hits=3,
            new_unique_pages=2,
            new_supporting_evidence_spans=5,
            new_independent_publishers=1,
        )
        expected = 3 + 2 + 5 + 2 * 1
        assert nt.marginal_gain == expected

    def test_publishers_weighted_2x(self):
        nt = NoveltyTracker(new_independent_publishers=4)
        assert nt.marginal_gain == 8

    def test_reset_clears_counters(self):
        nt = NoveltyTracker(new_unique_hits=10, new_unique_pages=5)
        nt = NoveltyTracker()
        assert nt.new_unique_hits == 0
        assert nt.new_unique_pages == 0
        assert nt.marginal_gain == 0


# ── Per-stage timeout tests
# ───────────────────────────────────────────────────


class TestPerStageTimeouts:
    def test_all_roles_have_timeouts(self):
        for role in AgentRole:
            assert role in _PER_STAGE_TIMEOUTS, (
                f"Missing timeout for {role.value}"
            )

    def test_stage_timeout_returns_value(self):
        for role in AgentRole:
            timeout = _stage_timeout(role)
            assert timeout > 0

    def test_unknown_role_gets_default(self):
        timeout = _stage_timeout(MagicMock())
        assert timeout == 30.0


# ── Budget from settings test
# ─────────────────────────────────────────────────


class TestBudgetFromSettings:
    def test_uses_workflow_config(self):
        budget = _budget_from_settings()
        assert budget.max_rounds > 0
        assert budget.max_tokens > 0
        assert budget.max_wall_seconds > 0
        assert budget.min_marginal_evidence >= 0
        assert budget.max_critic_revision_loops >= 0
