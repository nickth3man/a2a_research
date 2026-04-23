"""Tests for ErrorEnvelope model and error ledger."""

from __future__ import annotations

import pytest

from a2a_research.backend.core.models import ResearchSession
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.models.enums import AgentRole


def test_error_envelope_defaults() -> None:
    env = ErrorEnvelope(
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
    )
    assert env.role is None
    assert env.retryable is False
    assert env.root_cause == ""
    assert env.upstream_errors == []


def test_error_envelope_with_role() -> None:
    env = ErrorEnvelope(
        role=AgentRole.SEARCHER,
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
        retryable=True,
        root_cause="No hits found.",
        trace_id="abc123",
    )
    assert env.role == AgentRole.SEARCHER
    assert env.code == ErrorCode.NO_HITS
    assert env.severity == ErrorSeverity.DEGRADED
    assert env.retryable is True
    assert env.trace_id == "abc123"


def test_error_envelope_nested() -> None:
    inner = ErrorEnvelope(
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
    )
    outer = ErrorEnvelope(
        code=ErrorCode.BUDGET_EXHAUSTED_AFTER_GATHER,
        severity=ErrorSeverity.DEGRADED,
        upstream_errors=[inner],
    )
    assert len(outer.upstream_errors) == 1
    assert outer.upstream_errors[0].code == ErrorCode.NO_HITS


def test_session_has_trace_id() -> None:
    session = ResearchSession(query="test")
    assert session.trace_id
    assert len(session.trace_id) == 32  # uuid4().hex


def test_session_error_ledger_starts_empty() -> None:
    session = ResearchSession(query="test")
    assert session.error_ledger == []


def test_session_error_ledger_append() -> None:
    session = ResearchSession(query="test")
    env = ErrorEnvelope(
        role=AgentRole.PLANNER,
        code=ErrorCode.PLANNER_EMPTY,
        severity=ErrorSeverity.FATAL,
    )
    session.error_ledger.append(env)
    assert len(session.error_ledger) == 1
    assert session.error_ledger[0].code == ErrorCode.PLANNER_EMPTY


def test_error_codes_are_strings() -> None:
    assert ErrorCode.QUERY_REJECTED == "QUERY_REJECTED"
    assert ErrorCode.PLANNER_EMPTY == "PLANNER_EMPTY"


def test_error_severity_values() -> None:
    assert ErrorSeverity.FATAL == "fatal"
    assert ErrorSeverity.WARNING == "warning"
    assert ErrorSeverity.DEGRADED == "degraded"
