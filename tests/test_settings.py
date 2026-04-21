"""Tests for :mod:`a2a_research.settings`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

import a2a_research.settings as settings_module
from a2a_research.settings import AppSettings, LLMSettings, WorkflowConfig


class TestValidateDotenvKeys:
    def test_unknown_keys_log_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("UNKNOWN_KEY=value\nLLM_API_KEY=secret\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

        assert "Unknown keys in .env: UNKNOWN_KEY" in caplog.text

    def test_mesop_passthrough_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "MESOP_STATE_SESSION_BACKEND=memory\nLLM_API_KEY=secret\n"
        )

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

    def test_wf_prefix_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("WF_BUDGET_MAX_ROUNDS=3\nLLM_API_KEY=secret\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

    def test_expected_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LOG_LEVEL=INFO\n"
            "MESOP_PORT=32123\n"
            "WORKFLOW_TIMEOUT=120\n"
            "LLM_MODEL=m\n"
            "LLM_BASE_URL=https://example.com\n"
            "LLM_API_KEY=k\n"
            "TAVILY_API_KEY=tvly-...\n"
            "BRAVE_API_KEY=brave-...\n"
            "SEARCH_MAX_RESULTS=5\n"
            "RESEARCH_MAX_ROUNDS=3\n"
        )
        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()


class TestAppSettings:
    def test_model_validator_runs_dotenv_validation(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("BAD_KEY=value\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings = AppSettings()

        assert "Unknown keys in .env: BAD_KEY" in caplog.text
        assert isinstance(settings, AppSettings)

    def test_nested_llm_settings(self) -> None:
        env_file = Path(__file__).resolve().parents[3] / ".env"
        if not env_file.exists():
            with (
                patch("a2a_research.settings._ENV_FILE", env_file),
                patch("a2a_research.settings.dotenv_values", return_value={}),
            ):
                settings = AppSettings()
        else:
            with patch("a2a_research.settings.dotenv_values", return_value={}):
                settings = AppSettings()
        assert isinstance(settings.llm, LLMSettings)

    def test_llm_settings_defaults(self) -> None:
        with (
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict("os.environ", {}, clear=True),
        ):
            llm = LLMSettings()
        assert llm.model == "openrouter/elephant-alpha"
        assert llm.base_url == "https://openrouter.ai/api/v1"
        assert isinstance(llm.api_key, str)

    def test_llm_provider_legacy_key_does_not_warn(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("LLM_PROVIDER=openrouter\nLLM_API_KEY=secret\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

        assert "Unknown keys in .env" not in caplog.text

    def test_new_research_fields(self, tmp_path: Path) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict(
                "os.environ",
                {
                    "LLM_API_KEY": "k",
                    "TAVILY_API_KEY": "t",
                    "BRAVE_API_KEY": "b",
                },
                clear=True,
            ),
        ):
            s = AppSettings()
        assert s.research_max_rounds == 5
        assert s.search_max_results == 5
        assert s.tavily_api_key == "t"
        assert s.brave_api_key == "b"

    def test_app_settings_requires_llm_and_tavily_keys(
        self, tmp_path: Path
    ) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict(
                "os.environ",
                {"LLM_API_KEY": "", "TAVILY_API_KEY": "x"},
                clear=True,
            ),
            pytest.raises(ValidationError, match="LLM_API_KEY"),
        ):
            AppSettings()
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict(
                "os.environ",
                {"LLM_API_KEY": "x", "TAVILY_API_KEY": ""},
                clear=True,
            ),
            pytest.raises(ValidationError, match="TAVILY_API_KEY"),
        ):
            AppSettings()
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict(
                "os.environ",
                {
                    "LLM_API_KEY": "x",
                    "TAVILY_API_KEY": "x",
                    "BRAVE_API_KEY": "",
                },
                clear=True,
            ),
            pytest.raises(ValidationError, match="BRAVE_API_KEY"),
        ):
            AppSettings()

    def test_app_settings_has_workflow_config(self, tmp_path: Path) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict(
                "os.environ",
                {
                    "LLM_API_KEY": "k",
                    "TAVILY_API_KEY": "t",
                    "BRAVE_API_KEY": "b",
                },
                clear=True,
            ),
        ):
            s = AppSettings()
        assert isinstance(s.workflow, WorkflowConfig)
        assert s.workflow.budget_max_rounds == 5
        assert s.workflow.search_providers == ["tavily", "brave", "ddg"]


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
