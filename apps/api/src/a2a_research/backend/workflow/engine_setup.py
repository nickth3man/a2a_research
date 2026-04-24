"""Workflow setup stages: preprocess, clarify, plan."""

from __future__ import annotations

from typing import TYPE_CHECKING
import logfire

from a2a_research.backend.core.models import AgentRole, AgentStatus
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.agents import run_agent as _run_agent
from a2a_research.backend.workflow.claims import should_abort_preprocessing
from a2a_research.backend.workflow.coerce import coerce_claims, coerce_dag
from a2a_research.backend.workflow.engine_setup_helpers import (
    abort_for_preprocessing,
    emit_preprocess_warning,
    fail_for_empty_plan,
    finalize_plan,
    initialize_claim_state,
    warn_for_low_claim_coverage,
)
from a2a_research.backend.workflow.status import emit_step, set_status

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        Claim,
        ClaimDAG,
        ResearchSession,
        WorkflowBudget,
    )

__all__ = ["run_setup_stages"]


async def run_setup_stages(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
) -> tuple[str, list[Claim], ClaimDAG, list[str]] | None:
    """Run preprocess, clarify, and plan stages.

    Returns ``None`` if the workflow should abort early. Otherwise
    returns ``(committed_interpretation, claims, dag, seed_queries)``.
    """

    with logfire.span("workflow.setup", session_id=session.id):
        # ── Preprocess ──────────────────────────────────────────────────
        preprocess_result = await _run_agent(
            session,
            client,
            AgentRole.PREPROCESSOR,
            {
                "query": query,
                "session_id": session.id,
                "trace_id": session.trace_id,
            },
        )

        emit_preprocess_warning(session, preprocess_result)

        if should_abort_preprocessing(preprocess_result):
            abort_for_preprocessing(session, query)
            return None

        sanitized_query = preprocess_result.get("sanitized_query", query)
        query_class = preprocess_result.get(
            "query_class",
            preprocess_result.get("class", "factual"),
        )
        domain_hints = preprocess_result.get("domain_hints", [])

        # ── Clarify (back-channel: PRE→CLR) ─────────────────────────────
        clarify_result = await _run_agent(
            session,
            client,
            AgentRole.CLARIFIER,
            {
                "query": sanitized_query,
                "query_class": query_class,
                "session_id": session.id,
                "trace_id": session.trace_id,
                # Back-channel from PRE
                "normalization_rationale": preprocess_result.get(
                    "normalization_notes", ""
                ),
                "risky_spans": preprocess_result.get("risky_spans", []),
                "domain_hints": domain_hints,
            },
        )
        committed_interpretation = clarify_result.get(
            "committed_interpretation", sanitized_query
        )

        # ── Plan (back-channel: CLR→PLN) ─────────────────────────────────
        emit_step(
            session.id,
            AgentRole.PLANNER,
            ProgressPhase.STEP_STARTED,
            "planner_started",
        )
        set_status(
            session, AgentRole.PLANNER, AgentStatus.RUNNING, "Decomposing query…"
        )
        plan_result = await _run_agent(
            session,
            client,
            AgentRole.PLANNER,
            {
                "query": committed_interpretation,
                "domain_hints": domain_hints,
                "session_id": session.id,
                "trace_id": session.trace_id,
                # Back-channel from CLR
                "ambiguity_constraints": clarify_result.get("ambiguity_notes", ""),
                "interpretation_rationale": clarify_result.get(
                    "rejected_interpretations", []
                ),
            },
        )
        claims = coerce_claims(plan_result.get("claims", []))
        dag = coerce_dag(plan_result.get("claim_dag", {}), claims=claims)
        seed_queries = [
            str(q)
            for q in plan_result.get("seed_queries", [])
            if isinstance(q, str)
        ]

        if not claims:
            fail_for_empty_plan(session, query)
            return None

        min_claims = getattr(budget, "min_claims_threshold", 2)
        warn_for_low_claim_coverage(session, len(claims), min_claims)
        finalize_plan(session, claims, dag)
        initialize_claim_state(session, claims, dag)

        return committed_interpretation, claims, dag, seed_queries
