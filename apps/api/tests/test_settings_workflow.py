"""Tests for WorkflowConfig settings."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import ValidationError

from core import WorkflowConfig
from core.settings.settings_workflow_core import WorkflowConfigCore
from core.settings.settings_workflow_ext import WorkflowConfigExt
from core.settings.settings_workflow_ext_defaults import (
    DEFAULT_AB_TESTING_WEIGHTS,
    DEFAULT_CHECKPOINT_STAGES,
    DEFAULT_COST_ATTRIBUTION_TAGS,
    DEFAULT_OUTPUT_FORMATS,
    DEFAULT_TELEMETRY_TRACE_IDS,
)


class TestWorkflowConfigCore:
    def _make(
        self, env_overrides: dict[str, str] | None = None
    ) -> WorkflowConfigCore:
        with patch.dict("os.environ", env_overrides or {}, clear=False):
            return WorkflowConfigCore()

    def test_defaults(self) -> None:
        c = self._make()
        assert c.budget_max_rounds == 5
        assert c.search_providers == ["tavily", "brave", "ddg"]
        assert c.ranking_diversity_penalty == 0.3
        assert c.evidence_chunk_size == 1000

    def test_env_override(self) -> None:
        c = self._make({"WF_BUDGET_MAX_ROUNDS": "9"})
        assert c.budget_max_rounds == 9


class TestWorkflowConfigExt:
    def _make(
        self, env_overrides: dict[str, str] | None = None
    ) -> WorkflowConfigExt:
        with patch.dict("os.environ", env_overrides or {}, clear=False):
            return WorkflowConfigExt()

    def test_defaults(self) -> None:
        e = self._make()
        assert e.adversary_enabled is True
        assert e.output_formats == DEFAULT_OUTPUT_FORMATS
        assert e.checkpointing_stages == DEFAULT_CHECKPOINT_STAGES
        assert e.telemetry_trace_ids == DEFAULT_TELEMETRY_TRACE_IDS
        assert e.cost_attribution_tags == DEFAULT_COST_ATTRIBUTION_TAGS
        assert e.ab_testing_weights == DEFAULT_AB_TESTING_WEIGHTS

    def test_ab_weights_validation(self) -> None:
        with pytest.raises(ValidationError, match=r"sum to ~1.0"):
            self._make({"WF_AB_TESTING_WEIGHTS": '{"a":0.1}'})

    def test_ext_defaults_module_constants(self) -> None:
        assert "plan" in DEFAULT_CHECKPOINT_STAGES
        assert "session_id" in DEFAULT_TELEMETRY_TRACE_IDS
        assert "claim_id" in DEFAULT_COST_ATTRIBUTION_TAGS
        assert set(DEFAULT_AB_TESTING_WEIGHTS.keys()) == {
            "claim_recall",
            "citation_accuracy",
            "latency",
            "cost",
        }


class TestWorkflowConfig:
    def _make_wf(
        self, env_overrides: dict[str, str] | None = None
    ) -> WorkflowConfig:
        with patch.dict("os.environ", env_overrides or {}, clear=False):
            return WorkflowConfig()

    def test_all_defaults(self) -> None:
        wf = self._make_wf()
        assert wf.budget_max_rounds == 5
        assert wf.budget_max_tokens == 200_000
        assert wf.budget_max_wall_seconds == 180
        assert wf.budget_max_http_calls == 50
        assert wf.budget_min_marginal_evidence == 2
        assert wf.budget_max_critic_revision_loops == 2

        assert wf.search_providers == ["tavily", "brave", "ddg"]
        assert wf.search_parallel is True
        assert wf.search_max_results_per_provider == 5

        assert wf.ranking_enabled is True
        assert wf.ranking_fetch_budget == 8
        assert wf.ranking_diversity_penalty == 0.3
        assert wf.ranking_freshness_weight_default == 0.2

        assert wf.evidence_deduplication is True
        assert wf.evidence_chunk_size == 1000
        assert wf.evidence_chunk_overlap == 200
        assert wf.evidence_source_independence is True

        assert wf.adversary_enabled is True
        assert wf.adversary_trigger == "on_tentative_supported"
        assert wf.adversary_inversion_query_count == 3
        assert wf.adversary_counter_expert_lookup is True

        assert wf.verification_cache_results is True
        assert wf.verification_confidence_auto_accept_threshold == 0.9
        assert wf.verification_short_circuit_when_adversary_holds is True

        assert wf.synthesis_streaming == "sse_via_coordinator"
        assert (
            wf.synthesis_tentative_snapshot_strategy
            == "cheap_template_every_round_plus_full_on_exit"
        )

        assert wf.output_formats == ["markdown", "json"]
        assert wf.output_citation_style == "hyperlinked_footnotes"

        assert wf.checkpointing_enabled is True
        assert wf.checkpointing_stages == [
            "plan",
            "verify",
            "adversary_gate",
            "synthesize",
        ]

        assert wf.pii_query_egress == "hash_with_session_key"
        assert wf.pii_evidence_ingest == "mask"
        assert wf.pii_checkpoint_write == "mask"
        assert wf.pii_pre_synthesis == "mask"

        assert wf.telemetry_opentelemetry is True
        assert wf.telemetry_prometheus is True
        assert wf.telemetry_trace_log is True
        assert wf.telemetry_trace_ids == ["session_id", "trace_id", "span_id"]

        assert wf.cost_attribution_enabled is True
        assert wf.cost_attribution_tags == [
            "session_id",
            "claim_id",
            "user_id",
        ]

        assert wf.ab_testing_enabled is True
        assert wf.ab_testing_sampling == "per_query_class_sticky"
        assert wf.ab_testing_winner_metric == "weighted_composite"
        assert wf.ab_testing_weights == {
            "claim_recall": 0.35,
            "citation_accuracy": 0.35,
            "latency": 0.15,
            "cost": 0.15,
        }

    def test_env_override_nested_delimiter(self) -> None:
        wf = self._make_wf({"WF_BUDGET_MAX_ROUNDS": "10"})
        assert wf.budget_max_rounds == 10

    def test_env_override_flat_field(self) -> None:
        wf = self._make_wf({"WF_ADVERSARY_ENABLED": "false"})
        assert wf.adversary_enabled is False

    def test_validation_rejects_zero_max_rounds(self) -> None:
        with pytest.raises(ValidationError):
            self._make_wf({"WF_BUDGET_MAX_ROUNDS": "0"})

    def test_validation_rejects_negative_max_tokens(self) -> None:
        with pytest.raises(ValidationError):
            self._make_wf({"WF_BUDGET_MAX_TOKENS": "0"})

    def test_validation_rejects_diversity_penalty_out_of_range(self) -> None:
        with pytest.raises(ValidationError):
            self._make_wf({"WF_RANKING_DIVERSITY_PENALTY": "1.5"})

    def test_validation_rejects_confidence_threshold_out_of_range(
        self,
    ) -> None:
        with pytest.raises(ValidationError):
            self._make_wf(
                {"WF_VERIFICATION_CONFIDENCE_AUTO_ACCEPT_THRESHOLD": "1.5"}
            )

    def test_validation_weights_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match=r"sum to ~1\.0"):
            self._make_wf({"WF_AB_TESTING_WEIGHTS": '{"a":0.5,"b":0.2}'})

    def test_validation_accepts_valid_weights(self) -> None:
        wf = self._make_wf({"WF_AB_TESTING_WEIGHTS": '{"a":0.5,"b":0.5}'})
        assert wf.ab_testing_weights == {"a": 0.5, "b": 0.5}

    def test_model_dump_round_trip(self) -> None:
        wf = self._make_wf()
        dumped = wf.model_dump()
        wf2 = WorkflowConfig(**dumped)
        assert wf2 == wf
