"""Debug script to trace verify_result."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from a2a_research.backend.workflow import run_research_async
from a2a_research.backend.workflow.engine_verify import run_verify
from a2a_research.backend.workflow.engine_gather import gather_evidence
from tests.workflow_integration_fixtures import _configure_success_path
from tests.workflow_integration_helpers import _install_http_services

# Patch run_verify to debug
original_run_verify = run_verify

async def debug_run_verify(*args, **kwargs):
    result = await original_run_verify(*args, **kwargs)
    session = args[0]
    print(f"DEBUG run_verify: claim_state.verification = {session.claim_state.verification}")
    print(f"DEBUG run_verify: replan_reasons = {result}")
    return result

import a2a_research.backend.workflow.engine_verify as ev_mod
ev_mod.run_verify = debug_run_verify

# Patch gather_evidence to debug
original_gather_evidence = gather_evidence

async def debug_gather_evidence(*args, **kwargs):
    result = await original_gather_evidence(*args, **kwargs)
    print(f"DEBUG gather_evidence: result = {result}")
    return result

import a2a_research.backend.workflow.engine_gather as gath_mod
gath_mod.gather_evidence = debug_gather_evidence

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
