"""Main workflow driver for the v2 claim-centric engine."""

from __future__ import annotations

from time import perf_counter
from typing import TYPE_CHECKING

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.progress import ProgressPhase
from a2a_research.backend.workflow.status import emit_v2

if TYPE_CHECKING:
    from a2a_research.backend.core.a2a import A2AClient
    from a2a_research.backend.core.models import (
        ResearchSession,
        WorkflowBudget,
    )

logger = get_logger(__name__)

__all__ = ["drive_v2"]


async def drive_v2(
    session: ResearchSession,
    client: A2AClient,
    query: str,
    budget: WorkflowBudget,
) -> None:
    """Main v2 workflow driver."""
    from a2a_research.backend.workflow.engine_final import run_final_stages
    from a2a_research.backend.workflow.engine_loop import run_evidence_loop
    from a2a_research.backend.workflow.engine_setup import run_setup_stages

    workflow_start = perf_counter()

    setup = await run_setup_stages(session, client, query, budget)
    if setup is None:
        return

    _committed_interpretation, _claims, _dag, seed_queries = setup

    claim_state = session.claim_state
    assert claim_state is not None
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

    emit_v2(
        session.id, None, ProgressPhase.STEP_COMPLETED, "workflow_completed"
    )
