"""Tests for ClaimState."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from a2a_research.models import (
    Claim,
    ClaimDAG,
    ClaimDependency,
    ClaimState,
    ClaimVerification,
    Verdict,
)


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
