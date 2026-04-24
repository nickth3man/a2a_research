"""Main workflow driver."""

from __future__ import annotations

import json
from time import perf_counter
from typing import TYPE_CHECKING

import logfire

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.status import emit_step

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        ResearchSession,
        WorkflowBudget,
    )

logger = get_logger(__name__)

__all__ = ["drive"]


async def drive(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
) -> None:
    """Main workflow driver."""
    from a2a_research.backend.workflow.engine_final import run_final_stages
    from a2a_research.backend.workflow.engine_loop import run_evidence_loop
    from a2a_research.backend.workflow.engine_setup import run_setup_stages

    with logfire.span(
        "workflow.drive", session_id=session.id, query=query[:100]
    ):
        workflow_start = perf_counter()

        # Emit registry snapshot so frontend/bus sees agent capability map
        snapshot = client.build_registry_snapshot()
        emit_step(
            session.id,
            None,
            ProgressPhase.STEP_STARTED,
            "registry_snapshot",
            detail=json.dumps(snapshot),
        )

        setup = await run_setup_stages(session, client, query, budget)
        if setup is None:
            return

        _committed_interpretation, _claims, _dag, seed_queries = setup

        claim_state = session.claim_state
        if claim_state is None:
            msg = "Workflow setup completed without initializing claim_state."
            raise RuntimeError(msg)
        (
            claim_state,
            accumulated_evidence,
            provenance_tree,
        ) = await run_evidence_loop(
            session,
            client,
            query,
            budget,
            workflow_start,
            claim_state,
            seed_queries,
        )

        await run_final_stages(
            session,
            client,
            query,
            budget,
            claim_state,
            accumulated_evidence,
            provenance_tree,
        )

        # Populate session.claims from verified claim_state
        # for the API serializer.
        if claim_state and claim_state.original_claims:
            from a2a_research.backend.workflow.coerce import claims_from_state

            session.claims = claims_from_state(claim_state)

        emit_step(
            session.id,
            None,
            ProgressPhase.STEP_COMPLETED,
            "workflow_completed",
        )
