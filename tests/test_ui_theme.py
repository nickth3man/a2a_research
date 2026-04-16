"""Tests for UI theme color helpers."""

from __future__ import annotations

from a2a_research.models import AgentStatus
from a2a_research.ui.theme import status_color, verdict_bg, verdict_color


class TestStatusColor:
    def test_completed(self) -> None:
        assert status_color(AgentStatus.COMPLETED) == "#16a34a"

    def test_running(self) -> None:
        assert status_color(AgentStatus.RUNNING) == "#d97706"

    def test_failed(self) -> None:
        assert status_color(AgentStatus.FAILED) == "#dc2626"

    def test_pending_default(self) -> None:
        assert status_color(AgentStatus.PENDING) == "#9ca3af"


class TestVerdictColors:
    def test_supported(self) -> None:
        assert verdict_color("SUPPORTED") == "#16a34a"
        assert verdict_bg("SUPPORTED") == "#dcfce7"

    def test_refuted(self) -> None:
        assert verdict_color("REFUTED") == "#dc2626"
        assert verdict_bg("REFUTED") == "#fee2e2"

    def test_other_verdict_default(self) -> None:
        assert verdict_color("INSUFFICIENT_EVIDENCE") == "#d97706"
        assert verdict_bg("INSUFFICIENT_EVIDENCE") == "#fef3c7"
