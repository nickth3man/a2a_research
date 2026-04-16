"""Verifier role-specific helpers.

- :data:`SENDER` / :func:`build_payload` — A2A dispatch metadata.
- :func:`parse_verified_claims` plus its supporting parsers — JSON-first with a
  permissive line-oriented fallback.
"""

from __future__ import annotations

import json
import re
from typing import Any

from a2a_research.agents.pocketflow.utils.helpers import normalize_claim_id
from a2a_research.models import AgentRole, Claim, ResearchSession, Verdict, VerifierOutput
from a2a_research.providers import parse_structured_response

SENDER: AgentRole = AgentRole.ANALYST


def build_payload(session: ResearchSession) -> dict[str, Any]:
    analyst = session.get_agent(AgentRole.ANALYST)
    return {
        "claims": [c.model_dump() for c in analyst.claims],
        "query": session.query,
        "retrieved_chunks": [
            chunk.model_dump(mode="json") for chunk in session.retrieved_chunks
        ],
    }


def _parse_structured(raw: str) -> list[Claim] | None:
    structured = parse_structured_response(raw, VerifierOutput)
    if structured and structured.verified_claims:
        return [
            claim.model_copy(update={"id": normalize_claim_id(claim.id, f"clm_{i}")})
            for i, claim in enumerate(structured.verified_claims)
        ]
    return None


def _parse_raw_json(raw: str) -> list[Claim] | None:
    try:
        data = json.loads(raw) if raw.strip().startswith("{") else {}
    except Exception:
        data = {}
    if not (data and "verified_claims" in data):
        return None
    verified: list[Claim] = []
    for item in data["verified_claims"]:
        if not isinstance(item, dict):
            continue
        text = item.get("text", "")
        verdict_str = item.get("verdict", "INSUFFICIENT_EVIDENCE")
        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.INSUFFICIENT_EVIDENCE
        evidence_snippets = item.get("evidence_snippets", [])
        if not evidence_snippets and isinstance(item.get("reasoning"), str):
            evidence_snippets = [item["reasoning"]]
        verified.append(
            Claim(
                id=normalize_claim_id(item.get("id"), f"clm_{len(verified)}"),
                text=text,
                confidence=_coerce_confidence(item.get("confidence")),
                verdict=verdict,
                sources=item.get("sources", []),
                evidence_snippets=evidence_snippets,
            )
        )
    return verified


def _coerce_confidence(value: object, default: float = 0.5) -> float:
    """Best-effort numeric coercion for LLM-emitted confidence values.

    Normalises values on the 0-100 scale (e.g. ``85`` → ``0.85``) and clamps
    the result to [0.0, 1.0] to satisfy the :class:`~a2a_research.models.Claim`
    field constraint.
    """
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1.0:
            raw /= 100.0
        return max(0.0, min(1.0, raw))
    if isinstance(value, str):
        try:
            raw = float(value.strip().rstrip("%")) / (100.0 if "%" in value else 1.0)
            return max(0.0, min(1.0, raw))
        except ValueError:
            return default
    return default


def _parse_line_mode(raw: str) -> list[Claim]:
    lines = raw.split("\n")
    results: list[Claim] = []
    current_text: list[str] = []
    current_verdict: Verdict | None = None
    current_confidence: float = 0.5
    current_sources: list[str] = []
    current_snippets: list[str] = []

    for line in lines:
        line = line.strip()
        if not line:
            if current_text and current_verdict:
                results.append(
                    Claim(
                        id=f"clm_{len(results)}",
                        text=" ".join(current_text),
                        confidence=current_confidence,
                        verdict=current_verdict,
                        sources=current_sources,
                        evidence_snippets=current_snippets,
                    )
                )
                current_text, current_verdict, current_confidence = [], None, 0.5
                current_sources, current_snippets = [], []
            continue
        upper = line.upper()
        if "SUPPORTED" in upper and len(line) < 30:
            current_verdict = Verdict.SUPPORTED
            m = re.search(r"(\d+\.?\d*)%", line)
            if m:
                current_confidence = float(m.group(1)) / 100.0
        elif "REFUTED" in upper and len(line) < 30:
            current_verdict = Verdict.REFUTED
        elif "INSUFFICIENT" in upper and len(line) < 30:
            current_verdict = Verdict.INSUFFICIENT_EVIDENCE
        elif current_verdict and current_text:
            current_text.append(line)
        elif line.startswith("-") or (len(line) > 15 and not current_verdict):
            current_text.append(line.lstrip("- ").lstrip("*. "))

    if current_text and current_verdict:
        results.append(
            Claim(
                id=f"clm_{len(results)}",
                text=" ".join(current_text),
                confidence=current_confidence,
                verdict=current_verdict,
                sources=current_sources,
                evidence_snippets=current_snippets,
            )
        )
    return results


def parse_verified_claims(raw: str, fallback_claims: list[Claim]) -> list[Claim]:
    """Parse Verifier output with JSON-first strategy and permissive fallbacks."""
    structured = _parse_structured(raw)
    if structured is not None:
        return structured

    raw_json = _parse_raw_json(raw)
    if raw_json is not None:
        return raw_json

    results = _parse_line_mode(raw)
    if not results and fallback_claims:
        return list(fallback_claims)
    return results
