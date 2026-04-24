"""Debug script to check pytest-like workflow."""
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
    print(f"session.sources = {session.sources}")
    print(f"session.accumulated_evidence = {session.accumulated_evidence}")
    for role, result in session.agent_results.items():
        print(f"  {role.value}: {result.status.value} - {result.message}")
    
    await shared_client.aclose()
    mp.undo()

asyncio.run(main())
