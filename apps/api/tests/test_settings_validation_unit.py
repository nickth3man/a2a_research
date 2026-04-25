"""Tests for core.settings.settings_validation helpers."""

from __future__ import annotations

from unittest.mock import patch

from core.settings.settings_validation import validate_dotenv_keys


class TestValidateDotenvKeys:
    def test_unknown_key_warns(self) -> None:
        with (
            patch(
                "core.settings.dotenv_values",
                return_value={"EXTRA_KEY": "val"},
            ),
            patch(
                "core.settings.ENV_FILE",
                "/fake/.env",
            ),
        ):
            # Should not raise; unknown key triggers warning
            validate_dotenv_keys(expected_keys={"KNOWN_KEY"})

    def test_wf_prefixed_keys_are_passthrough(self) -> None:
        """WF_ prefixed keys are silently allowed (passthrough prefix)."""
        with (
            patch(
                "core.settings.dotenv_values",
                return_value={"WF_CUSTOM_SETTING": "val"},
            ),
            patch(
                "core.settings.ENV_FILE",
                "/fake/.env",
            ),
        ):
            # Should not warn — WF_ keys passthrough
            validate_dotenv_keys(expected_keys=set())
