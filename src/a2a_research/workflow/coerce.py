"""Type coercion helpers for converting agent responses to models."""

from __future__ import annotations

from typing import Any

from a2a.types import TaskState
from pydantic import ValidationError

from a2a_research.a2a import extract_data_payload_or_warn
from a2a_research.logging.app_logging import get_logger
from a2a_research.models import (
    Claim,
    ClaimDAG,
    ClaimFollowUp,
    ClaimState,
    ClaimVerification,
    EvidenceUnit,
    IndependenceGraph,
    ReplanReason,
    ReportOutput,
    Verdict,
)
from a2a_research.tools import PageContent, WebHit

logger = get_logger(__name__)

__all__ = [
    "coerce_claim_state",
    "coerce_claims",
    "coerce_dag",
    "coerce_evidence_unit",
    "coerce_follow_ups",
    "coerce_page_content",
    "coerce_replan_reasons",
    "coerce_report",
    "coerce_web_hit",
    "merge_verified_claims_into_state",
    "payload",
    "task_failed",
]


def payload(task: Any) -> dict[str, Any]:
    if task is None:
        return {}
    return extract_data_payload_or_warn(task)


def task_failed(task: Any) -> bool:
    status = getattr(task, "status", None)
    state = getattr(status, "state", None)
    return state == TaskState.TASK_STATE_FAILED


def coerce_claims(raw: Any) -> list[Claim]:
    claims: list[Claim] = []
    for item in raw or []:
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if isinstance(item, dict):
            try:
                claims.append(Claim.model_validate(item))
            except ValidationError:
                continue
    return claims


def coerce_dag(raw: Any, *, claims: list[Claim] | None = None) -> ClaimDAG:
    if isinstance(raw, ClaimDAG):
        dag = raw
    elif isinstance(raw, dict):
        try:
            dag = ClaimDAG.model_validate(raw)
        except ValidationError:
            dag = ClaimDAG()
    else:
        dag = ClaimDAG()
    if not dag.nodes and claims:
        dag.nodes = [claim.id for claim in claims]
    elif claims:
        known = set(dag.nodes)
        for claim in claims:
            if claim.id not in known:
                dag.nodes.append(claim.id)
                known.add(claim.id)
    return dag


def coerce_claim_state(
    raw: Any,
    *,
    fallback_claims: list[Claim] | None = None,
    fallback_dag: ClaimDAG | None = None,
) -> ClaimState | None:
    if isinstance(raw, ClaimState):
        state = raw
    elif isinstance(raw, dict):
        try:
            state = ClaimState.model_validate(raw)
        except ValidationError:
            state = None
    else:
        state = None
    if state is None:
        return None
    if fallback_claims and not state.original_claims:
        state.original_claims = fallback_claims
    if fallback_dag and not state.dag.nodes and not state.dag.edges:
        state.dag = fallback_dag
    state.refresh_resolution_lists()
    return state


def coerce_follow_ups(raw: Any) -> list[ClaimFollowUp]:
    result: list[ClaimFollowUp] = []
    for item in raw or []:
        if isinstance(item, ClaimFollowUp):
            result.append(item)
            continue
        if isinstance(item, dict):
            try:
                result.append(ClaimFollowUp.model_validate(item))
            except ValidationError:
                continue
    return result


def coerce_replan_reasons(raw: Any) -> list[ReplanReason]:
    result: list[ReplanReason] = []
    for item in raw or []:
        if isinstance(item, ReplanReason):
            result.append(item)
            continue
        if isinstance(item, dict):
            try:
                result.append(ReplanReason.model_validate(item))
            except ValidationError:
                continue
    return result


def coerce_evidence_unit(raw: Any) -> EvidenceUnit | None:
    if isinstance(raw, EvidenceUnit):
        return raw
    if isinstance(raw, dict):
        try:
            return EvidenceUnit.model_validate(raw)
        except ValidationError:
            pass
    return None


def coerce_web_hit(raw: Any) -> WebHit | None:
    if isinstance(raw, WebHit):
        return raw
    if isinstance(raw, dict):
        try:
            return WebHit.model_validate(raw)
        except ValidationError:
            pass
    return None


def coerce_page_content(raw: Any) -> PageContent | None:
    if isinstance(raw, PageContent):
        return raw
    if isinstance(raw, dict):
        try:
            return PageContent.model_validate(raw)
        except ValidationError:
            pass
    return None


def coerce_report(raw: Any) -> ReportOutput | None:
    if isinstance(raw, ReportOutput):
        return raw
    if isinstance(raw, dict):
        try:
            return ReportOutput.model_validate(raw)
        except ValidationError:
            pass
    return None


def merge_verified_claims_into_state(
    claim_state: ClaimState,
    verified_claims: list[Claim],
    independence_graph: IndependenceGraph,
) -> ClaimState:
    if not verified_claims:
        return claim_state
    for verified in verified_claims:
        verification = claim_state.verification.get(verified.id)
        if verification is None:
            verification = ClaimVerification(claim_id=verified.id)
            claim_state.verification[verified.id] = verification
        verification.verdict = verified.verdict
        verification.confidence = verified.confidence
        verification.independent_source_count = (
            independence_graph.independent_source_count(verified.id)
        )
        verification.supporting_evidence_ids = list(verified.sources)
        if verified.verdict == Verdict.REFUTED:
            claim_state.mark_dependents_stale(verified.id)
    claim_state.refresh_resolution_lists()
    return claim_state
