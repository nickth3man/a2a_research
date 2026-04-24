"""Shared telemetry utilities for LogFire integration."""

from __future__ import annotations

import os

import logfire

__all__ = ["configure_telemetry", "is_test_environment"]


def is_test_environment() -> bool:
    """Return True when running under pytest or in CI."""
    return (
        "PYTEST_CURRENT_TEST" in os.environ
        or "CI" in os.environ
        or "GITHUB_ACTIONS" in os.environ
    )


def configure_telemetry(
    *,
    service_name: str = "a2a-research",
    service_version: str = "0.2.0",
) -> None:
    """Configure LogFire with sensible defaults.

    In test/CI environments, telemetry is configured with
    ``send_to_logfire=False`` so tests never block on external
    connectivity.
    """
    test_mode = is_test_environment()
    logfire.configure(
        service_name=service_name,
        service_version=service_version,
        send_to_logfire="if-token-present",
        console=False if test_mode else None,
    )
