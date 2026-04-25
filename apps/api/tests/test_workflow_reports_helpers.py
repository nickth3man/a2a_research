"""Tests for workflow.reports string helpers."""

from __future__ import annotations

from workflow import reports as wr


def test_planner_failed_report_contains_query() -> None:
    t = wr.planner_failed_report("hello?")
    assert "hello?" in t
    assert "Planner failed" in t


def test_abort_report_includes_reason() -> None:
    t = wr.abort_report("q", "network down")
    assert "q" in t
    assert "network down" in t
    assert "unavailable" in t.lower()
