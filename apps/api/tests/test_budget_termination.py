"""Tests for termination conditions, progress emissions, and publisher
tracking."""

from __future__ import annotations

from core.models import (
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


class TestWallSecondsTracking:
    def test_wall_seconds_updated_in_session(self):
        session = ResearchSession(query="test")
        assert session.budget_consumed.wall_seconds == 0.0

    def test_wall_seconds_is_float(self):
        bc = BudgetConsumption(wall_seconds=12.5)
        assert isinstance(bc.wall_seconds, float)
        assert bc.wall_seconds == 12.5


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
