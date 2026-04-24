"""Debug script to check agent statuses."""
import asyncio
from a2a_research.backend.workflow import run_research_async
from a2a_research.backend.core.models import AgentStatus
from tests.workflow_integration_fixtures import _configure_success_path
from tests.workflow_integration_helpers import _install_http_services

class FakeMonkeyPatch:
    def setattr(self, obj, name, value):
        setattr(obj, name, value)

async def main():
    mp = FakeMonkeyPatch()
    _configure_success_path(mp)
    shared_client = _install_http_services(mp)

    session = await run_research_async("When did JWST launch?")

    print(f"session.error = {session.error}")
    print(f"session.sources = {session.sources}")
    print(f"session.report = {session.report}")

    for role, result in session.agent_results.items():
        print(f"  {role.value}: {result.status.value} - {result.message}")

    await shared_client.aclose()

asyncio.run(main())
