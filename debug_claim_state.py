"""Debug script to check claim state."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest

from a2a_research.backend.workflow import run_research_async
from tests.workflow_integration_fixtures import _configure_success_path
from tests.workflow_integration_helpers import _install_http_services

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
