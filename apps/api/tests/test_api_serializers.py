"""Tests for entrypoints.api_serializers helpers."""

from __future__ import annotations

from dataclasses import replace

from core import (
    AgentRole,
    Claim,
    ErrorEnvelope,
    ErrorSeverity,
    ProgressEvent,
    ProgressPhase,
    Verdict,
    WebSource,
)
from core.models.errors import ErrorCode
from entrypoints import api_serializers as ser


def test_normalize_role_none_and_deduplicator() -> None:
    assert ser.normalize_role(None) is None
    assert ser.normalize_role("planner") == "planner"
    assert ser.normalize_role("evidence_deduplicator") == "deduplicator"


def test_normalize_verdict() -> None:
    assert ser.normalize_verdict("SUPPORTED") == "SUPPORTED"
    assert ser.normalize_verdict("REFUTED") == "REFUTED"
    assert ser.normalize_verdict("other") == "UNVERIFIABLE"


def test_sse_line_format() -> None:
    s = ser.sse("ping", {"a": 1})
    assert s.startswith("event: ping\n")
    assert '"a": 1' in s


def test_serialize_envelope() -> None:
    env = ErrorEnvelope(
        code=ErrorCode.QUERY_REJECTED,
        severity=ErrorSeverity.FATAL,
        role=AgentRole.PLANNER,
    )
    d = ser.serialize_envelope(env)
    assert d["code"] == ErrorCode.QUERY_REJECTED
    assert d["role"] == "planner"


def test_serialize_progress_with_and_without_envelope() -> None:
    ev = ProgressEvent(
        session_id="s",
        phase=ProgressPhase.STEP_STARTED,
        role=AgentRole.PLANNER,
        step_index=0,
        total_steps=2,
        substep_label="x",
    )
    p = ser.serialize_progress(ev)
    assert p["type"] == "progress"
    assert "envelope" not in p

    ev2 = replace(
        ev,
        envelope=ErrorEnvelope(
            code=ErrorCode.PLANNER_EMPTY,
            severity=ErrorSeverity.WARNING,
        ),
    )
    p2 = ser.serialize_progress(ev2)
    assert "envelope" in p2


def test_serialize_claim_with_evidence_snippet() -> None:
    c = Claim(
        text="t",
        verdict=Verdict.SUPPORTED,
        confidence=0.9,
        sources=["u"],
        evidence_snippets=["evidence here"],
    )
    d = ser.serialize_claim(c)
    assert d["verdict"] == "SUPPORTED"
    assert d["evidence"] == "evidence here"


def test_serialize_claim_unverifiable_verdict() -> None:
    c = Claim(
        text="t",
        verdict=Verdict.UNRESOLVED,
        confidence=0.0,
        sources=[],
        evidence_snippets=[],
    )
    d = ser.serialize_claim(c)
    assert d["verdict"] == "UNVERIFIABLE"


def test_serialize_source() -> None:
    ws = WebSource(url="https://a", title="A")
    assert ser.serialize_source(ws) == {"url": "https://a", "title": "A"}


def test_serialize_result_includes_ledger() -> None:
    from types import SimpleNamespace

    s = SimpleNamespace(
        id="i1",
        final_report="r",
        sources=[],
        claims=[],
        error_ledger=[
            ErrorEnvelope(
                code=ErrorCode.NO_HITS,
                severity=ErrorSeverity.DEGRADED,
            )
        ],
        error=None,
    )
    d = ser.serialize_result(s)
    assert d["type"] == "result"
    assert d["session_id"] == "i1"
    assert len(d["diagnostics"]) == 1
