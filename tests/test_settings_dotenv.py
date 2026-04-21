"""Tests for dotenv key validation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

import a2a_research.settings as settings_module


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
