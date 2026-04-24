"""Tests for AppSettings and related configuration."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest

import a2a_research.backend.core.settings as settings_module
from a2a_research.backend.core.settings import AppSettings, LLMSettings

if TYPE_CHECKING:
    from collections.abc import Callable


class TestAppSettings:
    def test_model_validator_runs_dotenv_validation(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("BAD_KEY=value\n")

        with (
            patch(
                "a2a_research.backend.core.settings._ENV_FILE",
                env_file,
            ),
            patch(
                "a2a_research.backend.core.settings.ENV_FILE",
                env_file,
            ),
            patch(
                "a2a_research.backend.core.settings.settings_core._env_file",
                return_value=env_file,
            ),
        ):
            settings = AppSettings()

        assert "Unknown keys in .env: BAD_KEY" in caplog.text
        assert isinstance(settings, AppSettings)

    def test_nested_llm_settings(self) -> None:
        env_file = Path(__file__).resolve().parents[3] / ".env"
        if not env_file.exists():
            with (
                patch(
                    "a2a_research.backend.core.settings._ENV_FILE", env_file
                ),
                patch(
                    "a2a_research.backend.core.settings.dotenv_values",
                    return_value={},
                ),
            ):
                settings = AppSettings()
        else:
            with patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ):
                settings = AppSettings()
        assert isinstance(settings.llm, LLMSettings)

    def test_llm_settings_defaults(self) -> None:
        with (
            patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ),
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
        validate_dotenv_keys_name = "_validate_dotenv_keys"
        validate_dotenv_keys = cast(
            "Callable[[], None]",
            getattr(settings_module, validate_dotenv_keys_name),
        )

        with patch("a2a_research.backend.core.settings._ENV_FILE", env_file):
            validate_dotenv_keys()

        assert "Unknown keys in .env" not in caplog.text

    def test_new_research_fields(self, tmp_path: Path) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        with (
            patch(
                "a2a_research.backend.core.settings._ENV_FILE",
                empty_env,
            ),
            patch(
                "a2a_research.backend.core.settings.ENV_FILE",
                empty_env,
            ),
            patch(
                "a2a_research.backend.core.settings.settings_core._env_file",
                return_value=empty_env,
            ),
            patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ),
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
        assert s.api_key == ""
        assert s.max_concurrent_sessions == 5
        assert s.session_ttl_seconds == 900.0
        assert s.tavily_api_key == "t"
        assert s.brave_api_key == "b"
