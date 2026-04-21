"""Shared helpers for FactChecker LangGraph nodes (prompt building, parsing, task metadata)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from a2a_research.app_logging import get_logger
from a2a_research.json_utils import parse_json_safely
from a2a_research.models import Claim, Verdict

logger = get_logger(__name__)

if TYPE_CHECKING:
    from a2a_research.tools import PageContent

__all__ = [
    "build_verify_prompt",
    "clamp_conf",
    "parse_verifier",
    "task_error_metadata",
    "task_failed",
]


def task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return str(state).endswith("failed") if state is not None else False


def task_error_metadata(task: Any) -> str | None:
    status = getattr(task, "status", None)
    message = getattr(status, "message", None) if status is not None else None
    parts = getattr(message, "parts", None)
    if parts is not None:
        for part in parts:
            root = getattr(part, "root", part)
            text = getattr(root, "text", None)
            if isinstance(text, str) and text.strip():
                return text.strip()
    return None


def build_verify_prompt(
    query: str, claims: list[Claim], evidence: list[PageContent]
) -> str:
    claim_block = json.dumps(
        [
            {
                "id": c.id,
                "text": c.text,
                "verdict": c.verdict.value,
                "confidence": c.confidence,
            }
            for c in claims
        ]
    )
    evidence_block = json.dumps(
        [
            {"url": p.url, "title": p.title, "excerpt": p.markdown[:1200]}
            for p in evidence
            if not p.error and p.markdown
        ][:10]
    )
    return (
        f"Query: {query}\n\n"
        f"Claims (current state): {claim_block}\n\n"
        f"Evidence so far: {evidence_block}\n\n"
        "Return the JSON now."
    )


def parse_verifier(
    raw: str, *, fallback: list[Claim]
) -> tuple[list[Claim], list[str]]:
    data = parse_json_safely(raw)
    if not isinstance(data, dict):
        logger.warning("Verifier fallback path used for raw=%r", raw[:200])
        return fallback, []
    verified: list[Claim] = []
    for i, item in enumerate(data.get("verified_claims") or []):
        if not isinstance(item, dict):
            continue
        try:
            verdict = Verdict(
                str(item.get("verdict") or "NEEDS_MORE_EVIDENCE")
            )
        except ValueError:
            verdict = Verdict.NEEDS_MORE_EVIDENCE
        verified.append(
            Claim(
                id=str(item.get("id") or f"c{i}"),
                text=str(item.get("text") or "").strip() or f"claim_{i}",
                verdict=verdict,
                confidence=clamp_conf(item.get("confidence")),
                sources=[str(s) for s in (item.get("sources") or []) if s],
                evidence_snippets=[
                    str(s) for s in (item.get("evidence_snippets") or []) if s
                ],
            )
        )
    if not verified:
        logger.warning(
            "Verifier produced no valid claims; fallback path used for raw=%r",
            raw[:200],
        )
        verified = fallback
    follow = [
        str(q).strip()
        for q in (data.get("follow_up_queries") or [])
        if isinstance(q, str) and q.strip()
    ]
    return verified, follow


def clamp_conf(raw: Any, default: float = 0.5) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return default
    if value > 1.0:
        value = value / 100.0
    return max(0.0, min(1.0, value))
