"""Debug gather_evidence flow."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from a2a_research.backend.agents.smolagents.searcher import core as searcher_core
from a2a_research.backend.agents.smolagents.reader import core as reader_core
from a2a_research.backend.agents.pocketflow.planner import nodes as planner_nodes
from a2a_research.backend.agents.pocketflow.planner import nodes_base as planner_nodes_base
from a2a_research.backend.agents.langgraph.fact_checker import verify_route as fc_verify
from a2a_research.backend.agents.pydantic_ai.synthesizer import agent as synth_agent
from a2a_research.backend.agents.smolagents.searcher import agent as searcher_agent
from a2a_research.backend.agents.smolagents.reader import agent as reader_agent

# Apply patches
planner_model = MagicMock()
planner_model.ainvoke = AsyncMock(return_value=MagicMock(content='{"strategy": "temporal"}'))
planner_nodes.get_llm = lambda: planner_model
planner_nodes_base.get_llm = lambda: planner_model

searcher_agent.build_agent = lambda: MagicMock(run=lambda p: '{"queries_used": ["JWST launch date"], "hits": [{"url": "https://nasa.example/jwst", "title": "NASA JWST", "snippet": "launched 2021", "source": "tavily", "score": 0.9}]}')
searcher_core.build_agent = searcher_agent.build_agent

reader_agent.build_agent = lambda: MagicMock(run=lambda p: '{"pages": [{"url": "https://nasa.example/jwst", "title": "NASA JWST", "markdown": "# NASA\\n\\nJWST launched December 25, 2021.", "word_count": 6}]}')
reader_core.build_agent = reader_agent.build_agent

fc_verify.get_llm = lambda: MagicMock(ainvoke=AsyncMock(return_value=MagicMock(content='{"verified_claims": [{"id": "c0", "text": "JWST launched in December 2021.", "verdict": "SUPPORTED", "confidence": 0.95, "sources": ["https://nasa.example/jwst"]}], "follow_up_queries": []}')))

synth_agent.build_agent = lambda: MagicMock(run=lambda p: MagicMock(output=MagicMock(title="JWST Launch", summary="JWST launched in December 2021.", sections=[])))

from tests.workflow_integration_helpers import _install_http_services
mp = MagicMock()
mp.setattr = lambda obj, name, val: setattr(obj, name, val)
shared_client = _install_http_services(mp)

from a2a_research.backend.workflow import run_research_async

async def main():
    session = await run_research_async("When did JWST launch?")
    print(f"session.error = {session.error}")
    print(f"session.sources = {session.sources}")
    print(f"session.accumulated_evidence = {session.accumulated_evidence}")
    for role, result in session.agent_results.items():
        print(f"  {role.value}: {result.status.value}")
    await shared_client.aclose()

asyncio.run(main())
