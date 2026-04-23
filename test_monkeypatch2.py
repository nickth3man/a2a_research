"""Diagnostic script to verify monkeypatch behavior."""
from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from a2a_research.backend.agents.smolagents.searcher import core as searcher_core
from a2a_research.backend.agents.smolagents.searcher import agent as searcher_agent

print(f"searcher_core.build_agent = {searcher_core.build_agent}")
print(f"searcher_agent.build_agent = {searcher_agent.build_agent}")

# Apply patch like the test does
fake_agent = MagicMock()
fake_agent.run = MagicMock(return_value='{"queries_used": ["test"], "hits": []}')
searcher_core.build_agent = lambda: fake_agent

print(f"After patch: searcher_core.build_agent = {searcher_core.build_agent}")

# Now import searcher_main (like _install_http_services does)
from a2a_research.backend.agents.smolagents.searcher import main as searcher_main

# Build the HTTP app
app = searcher_main.build_http_app()
print(f"App built: {app}")

# Now let's check what search_queries sees
print(f"search_queries globals build_agent = {searcher_core.search_queries.__globals__.get('build_agent')}")

# Let's call search_queries directly with extra debugging
async def test_search():
    # Patch search_queries to debug
    original_search_queries = searcher_core.search_queries
    
    async def debug_search_queries(queries, *, session_id=""):
        print(f"DEBUG: search_queries called with queries={queries}")
        print(f"DEBUG: build_agent = {searcher_core.build_agent}")
        agent = searcher_core.build_agent()
        print(f"DEBUG: agent = {agent}")
        print(f"DEBUG: agent.run = {agent.run}")
        result = agent.run("test prompt")
        print(f"DEBUG: agent.run result = {result!r}")
        
        # Call original
        result = await original_search_queries(queries, session_id=session_id)
        print(f"DEBUG: original result = {result}")
        return result
    
    searcher_core.search_queries = debug_search_queries
    
    result = await searcher_core.search_queries(["test query"], session_id="test")
    print(f"Result: {result}")
    print(f"Hits: {result.hits}")
    print(f"Errors: {result.errors}")

asyncio.run(test_search())
