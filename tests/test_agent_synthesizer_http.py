"""HTTP contract test for the Synthesizer service."""

from __future__ import annotations

import httpx
import pytest
from a2a.types import Task

from a2a_research.a2a.client import extract_data_payloads
from a2a_research.agents.pydantic_ai.synthesizer import main as synth_main
from a2a_research.models import ReportOutput
from tests.http_harness import build_sdk_client, send_and_get_result


@pytest.mark.asyncio
async def test_synthesizer_http_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _fake_synthesize(
        query: str, claims: list[object], sources: list[object], *, session_id: str = ""
    ) -> ReportOutput:
        return ReportOutput(title="JWST Launch", summary="JWST launched in December 2021.")

    monkeypatch.setattr(synth_main, "synthesize", _fake_synthesize)

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=synth_main.build_http_app()),
        base_url="http://localhost:10005",
    ) as http_client:
        client = build_sdk_client(http_client, "http://localhost:10005")
        result = await send_and_get_result(
            client,
            payload={
                "query": "When did JWST launch?",
                "verified_claims": [],
                "sources": [],
            },
        )
    assert isinstance(result, Task)
    assert extract_data_payloads(result)[0]["report"]["title"] == "JWST Launch"
