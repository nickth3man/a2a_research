"""Tests for new SSE event phases and emit_envelope."""

from __future__ import annotations

import asyncio

import pytest

from a2a_research.backend.core.models import ResearchSession
from a2a_research.backend.core.models.enums import AgentRole
from a2a_research.backend.core.models.errors import (
    ErrorCode,
    ErrorEnvelope,
    ErrorSeverity,
)
from a2a_research.backend.core.progress import Bus, ProgressPhase
from a2a_research.backend.workflow.status import emit_envelope, emit_step


@pytest.fixture()
def session_with_queue() -> tuple[ResearchSession, asyncio.Queue]:  # type: ignore[type-arg]
    session = ResearchSession(query="test")
    queue: asyncio.Queue = asyncio.Queue()  # type: ignore[type-arg]
    Bus.register(session.id, queue)
    yield session, queue
    Bus.unregister(session.id)


def test_new_progress_phases_exist() -> None:
    assert ProgressPhase.WARNING == "warning"
    assert ProgressPhase.RETRYING == "retrying"
    assert ProgressPhase.DEGRADED_MODE == "degraded_mode"
    assert ProgressPhase.FINAL_DIAGNOSTICS == "final_diagnostics"


def test_emit_envelope_appends_to_ledger(session_with_queue) -> None:
    session, _queue = session_with_queue
    env = ErrorEnvelope(
        role=AgentRole.SEARCHER,
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
        root_cause="test",
        trace_id=session.trace_id,
    )
    emit_envelope(session.id, env, session)
    assert len(session.error_ledger) == 1
    assert session.error_ledger[0].code == ErrorCode.NO_HITS


def test_emit_envelope_puts_event_on_queue(session_with_queue) -> None:
    session, queue = session_with_queue
    env = ErrorEnvelope(
        role=AgentRole.SEARCHER,
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
    )
    emit_envelope(session.id, env, session)
    assert not queue.empty()
    event = queue.get_nowait()
    assert event.phase == ProgressPhase.DEGRADED_MODE
    assert event.envelope is env


def test_emit_envelope_fatal_maps_to_final_diagnostics(session_with_queue) -> None:
    session, queue = session_with_queue
    env = ErrorEnvelope(
        role=AgentRole.PLANNER,
        code=ErrorCode.PLANNER_EMPTY,
        severity=ErrorSeverity.FATAL,
    )
    emit_envelope(session.id, env, session)
    event = queue.get_nowait()
    assert event.phase == ProgressPhase.FINAL_DIAGNOSTICS


def test_emit_envelope_warning_maps_to_warning(session_with_queue) -> None:
    session, queue = session_with_queue
    env = ErrorEnvelope(
        role=AgentRole.PLANNER,
        code=ErrorCode.LOW_CLAIM_COVERAGE,
        severity=ErrorSeverity.WARNING,
    )
    emit_envelope(session.id, env, session)
    event = queue.get_nowait()
    assert event.phase == ProgressPhase.WARNING


def test_emit_step_with_envelope(session_with_queue) -> None:
    session, queue = session_with_queue
    env = ErrorEnvelope(
        code=ErrorCode.NO_HITS,
        severity=ErrorSeverity.DEGRADED,
    )
    emit_step(
        session.id,
        None,
        ProgressPhase.DEGRADED_MODE,
        "test",
        envelope=env,
    )
    event = queue.get_nowait()
    assert event.envelope is env
    assert event.phase == ProgressPhase.DEGRADED_MODE