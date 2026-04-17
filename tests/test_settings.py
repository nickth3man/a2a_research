"""Tests for :mod:`a2a_research.settings`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import a2a_research.settings as settings_module
from a2a_research.settings import AppSettings, LLMSettings


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
        env_file.write_text("MESOP_STATE_SESSION_BACKEND=memory\nLLM_API_KEY=secret\n")

        with patch("a2a_research.settings._ENV_FILE", env_file):
            settings_module._validate_dotenv_keys()

    def test_expected_keys_are_allowed(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text(
            "LOG_LEVEL=INFO\n"
            "MESOP_PORT=32123\n"
            "WORKFLOW_TIMEOUT=120\n"
            "LLM_PROVIDER=openrouter\n"
            "LLM_MODEL=m\n"
            "LLM_BASE_URL=https://example.com\n"
            "LLM_API_KEY=k\n"
            "TAVILY_API_KEY=tvly-...\n"
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
        assert llm.provider == "openrouter"
        assert llm.model == "openrouter/elephant-alpha"
        assert llm.base_url == "https://openrouter.ai/api/v1"
        assert isinstance(llm.api_key, str)

    def test_new_research_fields(self, tmp_path: Path) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        # Pydantic-settings binds env_file at class-definition time, so we also
        # override ``TAVILY_API_KEY`` via os.environ to guarantee the default path.
        with (
            patch("a2a_research.settings._ENV_FILE", empty_env),
            patch("a2a_research.settings.dotenv_values", return_value={}),
            patch.dict("os.environ", {"TAVILY_API_KEY": ""}, clear=True),
        ):
            s = AppSettings()
        assert s.research_max_rounds == 3
        assert s.search_max_results == 5
        assert s.tavily_api_key == ""
