"""Workflow final stages: synthesize, critique, postprocess."""

from __future__ import annotations

from typing import TYPE_CHECKING

from a2a_research.models import AgentRole, AgentStatus
from a2a_research.progress import ProgressPhase
from a2a_research.workflow.agents import run_agent as _run_agent
from a2a_research.workflow.coerce import coerce_report
from a2a_research.workflow.status import emit_v2, set_status

if TYPE_CHECKING:
    from a2a_research.a2a import A2AClient
    from a2a_research.models import (
        ClaimState,
        EvidenceUnit,
        ProvenanceTree,
        ResearchSession,
        WorkflowBudget,
    )

__all__ = ["run_final_stages"]


async def run_final_stages(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
    claim_state: ClaimState | None,
    accumulated_evidence: list[EvidenceUnit],
    provenance_tree: ProvenanceTree,
) -> None:
    """Run synthesize, critique, and postprocess stages."""

    # Final Synthesize
    emit_v2(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_STARTED,
        "synthesizer_started",
    )
    set_status(
        session, AgentRole.SYNTHESIZER, AgentStatus.RUNNING, "Writing report…"
    )
    syn_result = await _run_agent(
        session,
        client,
        AgentRole.SYNTHESIZER,
        {
            "query": query,
            "claim_state": (
                claim_state.model_dump(mode="json") if claim_state else {}
            ),
            "evidence": [
                e.model_dump(mode="json") for e in accumulated_evidence
            ],
            "provenance_tree": provenance_tree.model_dump(mode="json"),
            "tentative_report": (
                session.tentative_report.model_dump(mode="json")
                if session.tentative_report
                else None
            ),
            "session_id": session.id,
        },
    )
    report = coerce_report(syn_result.get("report"))
    session.report = report
    session.final_report = report.to_markdown() if report else ""
    set_status(
        session,
        AgentRole.SYNTHESIZER,
        AgentStatus.COMPLETED if report else AgentStatus.FAILED,
        "Report synthesized." if report else "Failed to synthesize report.",
    )
    emit_v2(
        session.id,
        AgentRole.SYNTHESIZER,
        ProgressPhase.STEP_COMPLETED if report else ProgressPhase.STEP_FAILED,
        "synthesizer_completed" if report else "synthesizer_failed",
    )

    # Critique
    critique_passed = True
    if report:
        crit_result = await _run_agent(
            session,
            client,
            AgentRole.CRITIC,
            {
                "report": report.model_dump(mode="json"),
                "claim_state": (
                    claim_state.model_dump(mode="json") if claim_state else {}
                ),
                "evidence": [
                    e.model_dump(mode="json") for e in accumulated_evidence
                ],
                "session_id": session.id,
            },
        )
        critique_passed = bool(crit_result.get("passed", True))
        session.critique = crit_result.get("critique", "")
        iteration_count = int(crit_result.get("iteration_count", 0))

        if (
            not critique_passed
            and iteration_count < budget.max_critic_revision_loops
        ):
            session.budget_consumed.critic_revision_loops += 1

    # Postprocess
    post_result = await _run_agent(
        session,
        client,
        AgentRole.POSTPROCESSOR,
        {
            "report": report.model_dump(mode="json") if report else {},
            "claim_state": (
                claim_state.model_dump(mode="json") if claim_state else {}
            ),
            "provenance_tree": provenance_tree.model_dump(mode="json"),
            "output_formats": ["markdown", "json"],
            "citation_style": "hyperlinked_footnotes",
            "warnings": [] if critique_passed else [session.critique],
            "session_id": session.id,
        },
    )
    session.formatted_outputs = post_result.get("formatted_outputs", {})
    if session.formatted_outputs.get("markdown"):
        session.final_report = session.formatted_outputs["markdown"]
