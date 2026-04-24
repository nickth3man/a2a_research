"""SSE serialization helpers for the API gateway."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from a2a_research.backend.core.models.claims import Claim
    from a2a_research.backend.core.models.errors import ErrorEnvelope
    from a2a_research.backend.core.models.reports import WebSource
    from a2a_research.backend.core.progress.progress_types import ProgressEvent

_ROLE_NORM: dict[str, str] = {"evidence_deduplicator": "deduplicator"}

PHASE_TO_EVENT: dict[str, str] = {
    "warning": "warning",
    "retrying": "retrying",
    "degraded_mode": "degraded_mode",
    "final_diagnostics": "final_diagnostics",
}


def normalize_role(role: str | None) -> str | None:
    if role is None:
        return None
    return _ROLE_NORM.get(role, role)


def normalize_verdict(verdict: str) -> str:
    if verdict in ("SUPPORTED", "REFUTED"):
        return verdict
    return "UNVERIFIABLE"


def sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def serialize_envelope(envelope: ErrorEnvelope) -> dict[str, Any]:
    return {
        "role": normalize_role(str(envelope.role) if envelope.role else None),
        "code": envelope.code,
        "severity": envelope.severity,
        "retryable": envelope.retryable,
        "root_cause": envelope.root_cause,
        "remediation": envelope.remediation,
        "trace_id": envelope.trace_id,
    }


def serialize_progress(event: ProgressEvent) -> dict[str, Any]:
    data: dict[str, Any] = {
        "type": "progress",
        "session_id": event.session_id,
        "phase": event.phase,
        "role": normalize_role(str(event.role) if event.role else None),
        "step_index": event.step_index,
        "total_steps": event.total_steps,
        "substep_label": event.substep_label,
        "substep_index": event.substep_index,
        "substep_total": event.substep_total,
        "detail": event.detail,
        "elapsed_ms": event.elapsed_ms,
    }
    if event.envelope is not None:
        data["envelope"] = serialize_envelope(event.envelope)
    return data


def serialize_claim(claim: Claim) -> dict[str, Any]:
    return {
        "text": claim.text,
        "verdict": normalize_verdict(str(claim.verdict)),
        "confidence": claim.confidence,
        "sources": list(claim.sources),
        "evidence": (
            claim.evidence_snippets[0] if claim.evidence_snippets else None
        ),
    }


def serialize_source(source: WebSource) -> dict[str, str]:
    return {"url": source.url, "title": source.title}


def serialize_result(session: Any) -> dict[str, Any]:
    return {
        "type": "result",
        "session_id": session.id,
        "report": session.final_report,
        "sources": [serialize_source(s) for s in session.sources],
        "claims": [serialize_claim(c) for c in session.claims],
        "diagnostics": [serialize_envelope(e) for e in session.error_ledger],
        "error": session.error,
    }
