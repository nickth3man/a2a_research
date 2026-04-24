"""AppSettings validation and workflow config tests."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from a2a_research.backend.core.settings import AppSettings, WorkflowConfig

if TYPE_CHECKING:
    from pathlib import Path


class TestAppSettingsValidation:
    def test_app_settings_requires_llm_and_tavily_keys(
        self, tmp_path: Path
    ) -> None:
        empty_env = tmp_path / ".env"
        empty_env.write_text("")
        with (
            patch("a2a_research.backend.core.settings._ENV_FILE", empty_env),
            patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ),
            patch.dict(
                "os.environ",
                {"LLM_API_KEY": "", "TAVILY_API_KEY": "x"},
                clear=True,
            ),
            pytest.raises(ValidationError, match="LLM_API_KEY"),
        ):
            AppSettings()
        with (
            patch("a2a_research.backend.core.settings._ENV_FILE", empty_env),
            patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ),
            patch.dict(
                "os.environ",
                {"LLM_API_KEY": "x", "TAVILY_API_KEY": ""},
                clear=True,
            ),
            pytest.raises(ValidationError, match="TAVILY_API_KEY"),
        ):
            AppSettings()
        with (
            patch("a2a_research.backend.core.settings._ENV_FILE", empty_env),
            patch(
                "a2a_research.backend.core.settings.dotenv_values",
                return_value={},
            ),
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
            patch("a2a_research.backend.core.settings._ENV_FILE", empty_env),
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
        assert isinstance(s.workflow, WorkflowConfig)
        assert s.workflow.budget_max_rounds == 5
        assert s.workflow.search_providers == ["tavily", "brave", "ddg"]
