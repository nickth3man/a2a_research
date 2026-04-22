"""End-to-end workflow pipeline flow test over in-memory HTTP A2A services."""

from __future__ import annotations

import pytest

from a2a_research.backend.core.models import AgentStatus
from a2a_research.backend.workflow import run_research_async
from tests.workflow_integration_helpers import (
    _configure_success_path,
    _install_http_services,
)


@pytest.mark.asyncio
async def test_full_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    _configure_success_path(monkeypatch)
    shared_client = _install_http_services(monkeypatch)

    session = await run_research_async("When did JWST launch?")

    assert session.error is None
    assert session.report is not None
    assert session.report.title == "JWST Launch"
    assert "JWST" in session.final_report
    assert len(session.sources) == 1
    assert session.sources[0].url == "https://nasa.example/jwst"
    statuses = {
        role: result.status for role, result in session.agent_results.items()
    }
    assert all(status == AgentStatus.COMPLETED for status in statuses.values())
    await shared_client.aclose()
