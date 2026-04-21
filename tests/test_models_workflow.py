"""Tests for BudgetConsumption, NoveltyTracker, ClaimState, ClaimVerification, VerificationRevision."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import (
    BudgetConsumption,
    Claim,
    ClaimDAG,
    ClaimDependency,
    ClaimState,
    ClaimVerification,
    NoveltyTracker,
    Verdict,
    VerificationRevision,
    WorkflowBudget,
)


class TestVerificationRevision:
    def test_creation(self):
        rev = VerificationRevision(
            previous_verdict="UNRESOLVED",
            new_verdict="SUPPORTED",
            reason="Found 3 independent sources",
            evidence_delta=["ev1", "ev2", "ev3"],
        )
        assert rev.previous_verdict == "UNRESOLVED"
        assert rev.new_verdict == "SUPPORTED"
        assert rev.reason == "Found 3 independent sources"
        assert len(rev.evidence_delta) == 3
        assert rev.timestamp is not None

    def test_default_evidence_delta_empty(self):
        rev = VerificationRevision(
            previous_verdict="SUPPORTED",
            new_verdict="STALE",
            reason="Parent claim refuted",
        )
        assert rev.evidence_delta == []

    def test_invalid_verdict(self):
        with pytest.raises(ValidationError):
            VerificationRevision(
                previous_verdict="INVALID",
                new_verdict="SUPPORTED",
                reason="test",
            )

    def test_all_verdict_pairs(self):
        valid = ["SUPPORTED", "REFUTED", "MIXED", "UNRESOLVED", "STALE"]
        for prev in valid:
            for new in valid:
                rev = VerificationRevision(
                    previous_verdict=prev, new_verdict=new, reason="test"
                )
                assert rev.previous_verdict == prev
                assert rev.new_verdict == new

    def test_serialization_roundtrip(self):
        rev = VerificationRevision(
            previous_verdict="MIXED",
            new_verdict="SUPPORTED",
            reason="New evidence",
            evidence_delta=["ev_new"],
        )
        data = rev.model_dump()
        restored = VerificationRevision.model_validate(data)
        assert restored.previous_verdict == rev.previous_verdict
        assert restored.new_verdict == rev.new_verdict
        assert restored.evidence_delta == rev.evidence_delta


class TestClaimVerification:
    def test_defaults(self):
        cv = ClaimVerification(claim_id="clm_1")
        assert cv.verdict == Verdict.UNRESOLVED
        assert cv.confidence == 0.0
        assert cv.independent_source_count == 0
        assert cv.supporting_evidence_ids == []
        assert cv.refuting_evidence_ids == []
        assert cv.contradictions == []
        assert cv.adversary_result == "NOT_RUN"
        assert cv.revision_history == []

    def test_custom_values(self):
        cv = ClaimVerification(
            claim_id="clm_1",
            verdict=Verdict.SUPPORTED,
            confidence=0.85,
            independent_source_count=3,
            supporting_evidence_ids=["ev1", "ev2"],
            adversary_result="HOLDS",
        )
        assert cv.verdict == Verdict.SUPPORTED
        assert cv.confidence == 0.85
        assert cv.adversary_result == "HOLDS"

    def test_all_adversary_results(self):
        for result in ("HOLDS", "WEAKENED", "REFUTED", "NOT_RUN"):
            cv = ClaimVerification(claim_id="c", adversary_result=result)
            assert cv.adversary_result == result

    def test_invalid_adversary_result(self):
        with pytest.raises(ValidationError):
            ClaimVerification(claim_id="c", adversary_result="INVALID")


class TestClaimState:
    def test_empty_state(self):
        cs = ClaimState()
        assert cs.all_resolved is True
        assert cs.unresolved_or_stale_claims == []
        assert cs.unresolved_or_stale_claim_ids == []
        assert cs.tentatively_supported_claim_ids == []
        assert cs.freshness_windows == {}

    def test_all_resolved_when_unresolved(self):
        cs = ClaimState(unresolved_claim_ids=["c1"])
        assert cs.all_resolved is False

    def test_all_resolved_when_stale(self):
        cs = ClaimState(stale_claim_ids=["c1"])
        assert cs.all_resolved is False

    def test_all_resolved_when_both_empty(self):
        cs = ClaimState(resolved_claim_ids=["c1"])
        assert cs.all_resolved is True

    def test_mark_dependents_stale(self):
        claims = [Claim(id="a", text="root"), Claim(id="b", text="child")]
        dag = ClaimDAG(
            nodes=["a", "b"],
            edges=[ClaimDependency(parent_id="a", child_id="b")],
        )
        cs = ClaimState(
            original_claims=claims,
            dag=dag,
            verification={
                "b": ClaimVerification(claim_id="b", verdict=Verdict.SUPPORTED)
            },
        )
        cs.mark_dependents_stale("a")
        assert cs.verification["b"].verdict == Verdict.STALE
        assert "b" in cs.stale_claim_ids

    def test_mark_dependents_stale_removes_from_resolved(self):
        claims = [Claim(id="a", text="root"), Claim(id="b", text="child")]
        dag = ClaimDAG(
            nodes=["a", "b"],
            edges=[ClaimDependency(parent_id="a", child_id="b")],
        )
        cs = ClaimState(
            original_claims=claims,
            dag=dag,
            verification={"b": ClaimVerification(claim_id="b")},
            resolved_claim_ids=["b"],
        )
        cs.mark_dependents_stale("a")
        assert "b" not in cs.resolved_claim_ids

    def test_mark_dependents_stale_no_descendants(self):
        cs = ClaimState(
            original_claims=[Claim(id="a", text="leaf")],
            dag=ClaimDAG(nodes=["a"]),
        )
        cs.mark_dependents_stale("a")
        assert cs.stale_claim_ids == []

    def test_mark_dependents_stale_cascading(self):
        claims = [
            Claim(id="a", text="root"),
            Claim(id="b", text="mid"),
            Claim(id="c", text="leaf"),
        ]
        dag = ClaimDAG(
            nodes=["a", "b", "c"],
            edges=[
                ClaimDependency(parent_id="a", child_id="b"),
                ClaimDependency(parent_id="b", child_id="c"),
            ],
        )
        cs = ClaimState(
            original_claims=claims,
            dag=dag,
            verification={
                "b": ClaimVerification(claim_id="b"),
                "c": ClaimVerification(claim_id="c"),
            },
        )
        cs.mark_dependents_stale("a")
        assert cs.verification["b"].verdict == Verdict.STALE
        assert cs.verification["c"].verdict == Verdict.STALE

    def test_tentatively_supported(self):
        cs = ClaimState(
            verification={
                "c1": ClaimVerification(
                    claim_id="c1",
                    verdict=Verdict.SUPPORTED,
                    adversary_result="NOT_RUN",
                ),
                "c2": ClaimVerification(
                    claim_id="c2",
                    verdict=Verdict.SUPPORTED,
                    adversary_result="HOLDS",
                ),
                "c3": ClaimVerification(
                    claim_id="c3", verdict=Verdict.REFUTED
                ),
            },
        )
        assert cs.tentatively_supported_claim_ids == ["c1"]

    def test_unresolved_or_stale_claims(self):
        c1 = Claim(id="c1", text="unresolved")
        c2 = Claim(id="c2", text="stale")
        c3 = Claim(id="c3", text="resolved")
        cs = ClaimState(
            original_claims=[c1, c2, c3],
            unresolved_claim_ids=["c1"],
            stale_claim_ids=["c2"],
        )
        result = cs.unresolved_or_stale_claims
        ids = {c.id for c in result}
        assert ids == {"c1", "c2"}

    def test_unresolved_or_stale_claim_ids_dedup(self):
        cs = ClaimState(unresolved_claim_ids=["c1"], stale_claim_ids=["c1"])
        assert cs.unresolved_or_stale_claim_ids == ["c1"]

    def test_freshness_windows(self):
        from a2a_research.models import FreshnessWindow

        c1 = Claim(
            id="c1", text="t", freshness=FreshnessWindow(max_age_days=7)
        )
        cs = ClaimState(original_claims=[c1])
        assert "c1" in cs.freshness_windows
        assert cs.freshness_windows["c1"].max_age_days == 7


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
