"""Debug script to trace verify_result in detail."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from a2a_research.backend.workflow import run_research_async
from a2a_research.backend.workflow.engine_verify import run_verify
from a2a_research.backend.workflow.coerce import coerce_claims, merge_verified_claims_into_state
from tests.workflow_integration_fixtures import _configure_success_path
from tests.workflow_integration_helpers import _install_http_services

# Patch run_verify to debug
original_run_verify = run_verify

async def debug_run_verify(*args, **kwargs):
    session = args[0]
    client = args[1]
    query = args[2]
    budget = args[3]
    claim_state = args[4]
    to_process = args[5]
    pages = args[6]
    deduped_new = args[7]
    accumulated_evidence = args[8]
    independence_graph = args[9]
    provenance_tree = args[10]
    
    print(f"DEBUG run_verify START: deduped_new={len(deduped_new)}")
    print(f"DEBUG run_verify START: claim_state.verification={claim_state.verification}")
    
    from a2a_research.backend.workflow.agents import run_agent as _run_agent
    from a2a_research.backend.workflow.status import emit_step
    from a2a_research.backend.core.models import AgentRole
    from a2a_research.backend.core.progress import ProgressPhase
    from a2a_research.backend.workflow.coerce import coerce_claim_state, coerce_claims, coerce_follow_ups, coerce_replan_reasons, merge_verified_claims_into_state
    from a2a_research.backend.workflow.status import emit_envelope
    from a2a_research.backend.core.models.errors import ErrorCode, ErrorEnvelope, ErrorSeverity
    from a2a_research.backend.workflow.provenance import challenge_node_id, claim_node_id, ensure_edge, ensure_node, verdict_node_id
    from a2a_research.backend.core.models import ProvenanceNode, ProvenanceEdgeType, Verdict
    
    if not deduped_new:
        print("DEBUG run_verify: no deduped_new, returning early")
        return []
    
    emit_step(session.id, AgentRole.FACT_CHECKER, ProgressPhase.STEP_STARTED, "verifying_claims")
    verify_result = await _run_agent(
        session, client, AgentRole.FACT_CHECKER,
        {
            "query": query,
            "claims": [c.model_dump(mode="json") for c in to_process],
            "claim_dag": claim_state.dag.model_dump(mode="json"),
            "evidence": [p.model_dump(mode="json") for p in pages],
            "new_evidence": [e.model_dump(mode="json") for e in deduped_new],
            "accumulated_evidence": [e.model_dump(mode="json") for e in accumulated_evidence],
            "independence_graph": independence_graph.model_dump(mode="json"),
            "session_id": session.id,
            "trace_id": session.trace_id,
            "extraction_confidence": {getattr(p, "url", ""): getattr(p, "confidence", 1.0) for p in pages},
        },
    )
    
    print(f"DEBUG verify_result keys: {list(verify_result.keys())}")
    print(f"DEBUG verify_result verified_claims: {verify_result.get('verified_claims', [])}")
    
    raw_claims = verify_result.get("verified_claims", [])
    coerced = coerce_claims(raw_claims)
    print(f"DEBUG coerced claims: {coerced}")
    
    updated_state = coerce_claim_state(
        verify_result.get("updated_claim_state", {}),
        fallback_claims=claim_state.original_claims,
        fallback_dag=claim_state.dag,
    )
    print(f"DEBUG updated_state: {updated_state}")
    
    if updated_state:
        claim_state = updated_state
        print("DEBUG using updated_state")
    else:
        claim_state = merge_verified_claims_into_state(
            claim_state, coerced, independence_graph,
        )
        print(f"DEBUG after merge: claim_state.verification={claim_state.verification}")
    
    claim_state.refresh_resolution_lists()
    session.claim_state = claim_state
    
    coerce_follow_ups(verify_result.get("claim_follow_ups", []))
    replan_reasons = coerce_replan_reasons(verify_result.get("replan_reasons", []))
    session.replan_reasons = replan_reasons
    
    print(f"DEBUG run_verify END: claim_state.verification={claim_state.verification}")
    print(f"DEBUG replan_reasons={replan_reasons}")
    
    return replan_reasons

import a2a_research.backend.workflow.engine_verify as ev_mod
ev_mod.run_verify = debug_run_verify

async def main():
    mp = pytest.MonkeyPatch()
    _configure_success_path(mp)
    shared_client = _install_http_services(mp)
    
    session = await run_research_async("When did JWST launch?")
    
    print(f"session.error = {session.error}")
    print(f"claim_state.verification = {session.claim_state.verification}")
    print(f"tentatively_supported = {session.claim_state.tentatively_supported_claim_ids}")
    for role, result in session.agent_results.items():
        print(f"  {role.value}: {result.status.value}")
    
    await shared_client.aclose()
    mp.undo()

asyncio.run(main())
