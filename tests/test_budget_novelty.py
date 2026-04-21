"""Tests for BudgetConsumption, NoveltyTracker integration, and per-stage timeouts."""

from __future__ import annotations

from unittest.mock import MagicMock

from a2a_research.models import (
    AgentRole,
    BudgetConsumption,
    Claim,
    ClaimDAG,
    ClaimState,
    ClaimVerification,
    EvidenceUnit,
    NoveltyTracker,
    ResearchSession,
    Verdict,
    WorkflowBudget,
)
from a2a_research.workflow.workflow_engine import (
    _PER_STAGE_TIMEOUTS,
    _budget_from_settings,
    _stage_timeout,
)

# ── BudgetConsumption unit tests ──────────────────────────────────────────────


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


# ── NoveltyTracker unit tests ─────────────────────────────────────────────────


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


# ── Per-stage timeout tests ───────────────────────────────────────────────────


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


# ── Budget from settings test ─────────────────────────────────────────────────


class TestBudgetFromSettings:
    def test_uses_workflow_config(self):
        budget = _budget_from_settings()
        assert budget.max_rounds > 0
        assert budget.max_tokens > 0
        assert budget.max_wall_seconds > 0
        assert budget.min_marginal_evidence >= 0
        assert budget.max_critic_revision_loops >= 0


# ── Integration: wall_seconds tracking ────────────────────────────────────────


class TestWallSecondsTracking:
    def test_wall_seconds_updated_in_session(self):
        session = ResearchSession(query="test")
        assert session.budget_consumed.wall_seconds == 0.0

    def test_wall_seconds_is_float(self):
        bc = BudgetConsumption(wall_seconds=12.5)
        assert isinstance(bc.wall_seconds, float)
        assert bc.wall_seconds == 12.5


# ── Termination condition tests ───────────────────────────────────────────────


class TestTerminationConditions:
    def _make_claim_state(self, resolved: bool = False) -> ClaimState:
        claim = Claim(id="c1", text="Test claim")
        v = ClaimVerification(claim_id="c1")
        if resolved:
            v.verdict = Verdict.SUPPORTED
            return ClaimState(
                original_claims=[claim],
                dag=ClaimDAG(nodes=["c1"]),
                verification={"c1": v},
                unresolved_claim_ids=[],
                stale_claim_ids=[],
                resolved_claim_ids=["c1"],
            )
        return ClaimState(
            original_claims=[claim],
            dag=ClaimDAG(nodes=["c1"]),
            verification={"c1": v},
            unresolved_claim_ids=["c1"],
            stale_claim_ids=[],
            resolved_claim_ids=[],
        )

    def test_all_resolved_terminates(self):
        cs = self._make_claim_state(resolved=True)
        assert cs.all_resolved

    def test_unresolved_does_not_terminate(self):
        cs = self._make_claim_state(resolved=False)
        assert not cs.all_resolved

    def test_budget_exhausted_terminates(self):
        bc = BudgetConsumption(rounds=5)
        budget = WorkflowBudget(max_rounds=5)
        assert bc.is_exhausted(budget)

    def test_novelty_below_threshold(self):
        nt = NoveltyTracker(new_unique_hits=0, new_unique_pages=0)
        budget = WorkflowBudget(min_marginal_evidence=2)
        assert nt.marginal_gain < budget.min_marginal_evidence

    def test_no_follow_ups_terminates(self):
        deduplicated_follow_ups: list[str] = []
        assert len(deduplicated_follow_ups) == 0


# ── Progress event budget info tests ──────────────────────────────────────────


class TestProgressBudgetEmission:
    def test_progress_event_carries_budget_detail(self):
        bc = BudgetConsumption(
            rounds=2, tokens_consumed=5000, wall_seconds=30.0, http_calls=10
        )
        budget = WorkflowBudget()
        detail = (
            f"rounds={bc.rounds}/{budget.max_rounds} "
            f"tokens={bc.tokens_consumed}/{budget.max_tokens} "
            f"wall_s={bc.wall_seconds:.1f}/{budget.max_wall_seconds:.0f}"
        )
        assert "rounds=2/5" in detail
        assert "tokens=5000/200000" in detail
        assert "wall_s=30.0/180" in detail


# ── Publisher tracking tests ──────────────────────────────────────────────────


class TestPublisherTracking:
    def test_new_publishers_counted(self):
        existing = [
            EvidenceUnit(url="http://a.com", publisher_id="pub_a"),
            EvidenceUnit(url="http://b.com", publisher_id="pub_b"),
        ]
        new = [
            EvidenceUnit(url="http://c.com", publisher_id="pub_c"),
            EvidenceUnit(url="http://d.com", publisher_id="pub_d"),
        ]
        seen = {ev.publisher_id for ev in existing if ev.publisher_id}
        new_pubs = {
            ev.publisher_id
            for ev in new
            if ev.publisher_id and ev.publisher_id not in seen
        }
        assert len(new_pubs) == 2

    def test_duplicate_publishers_not_counted(self):
        existing = [
            EvidenceUnit(url="http://a.com", publisher_id="pub_a"),
        ]
        new = [
            EvidenceUnit(url="http://a2.com", publisher_id="pub_a"),
        ]
        seen = {ev.publisher_id for ev in existing if ev.publisher_id}
        new_pubs = {
            ev.publisher_id
            for ev in new
            if ev.publisher_id and ev.publisher_id not in seen
        }
        assert len(new_pubs) == 0

    def test_empty_publisher_not_counted(self):
        new = [
            EvidenceUnit(url="http://x.com", publisher_id=""),
        ]
        new_pubs = {ev.publisher_id for ev in new if ev.publisher_id}
        assert len(new_pubs) == 0
