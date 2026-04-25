"""smolagents ``Tool`` subclass wrapping
:func:`a2a_research.tools.search.web_search`.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from smolagents import Tool

from tools import web_search

__all__ = ["WebSearchTool"]


class WebSearchTool(Tool):
    name = "web_search"
    description = (
        "Search the web in parallel across Tavily and DuckDuckGo, returning a "
        "deduplicated ranked list of hits for a single query string."
    )
    inputs: ClassVar[dict[str, Any]] = {
        # smolagents Tool requires this as a class attribute
        "query": {
            "type": "string",
            "description": "Natural-language search query (keep it focused).",
        },
    }
    output_type = "array"

    def forward(self, query: str) -> list[dict[str, Any]]:
        result = _run(web_search(query))
        return [h.model_dump(mode="json") for h in result.hits]


def _run(coro: Any) -> Any:
    """Run an async call from a sync smolagents tool.

    Tools execute in the agent's sync ``run`` loop; if an event loop is already
    running in another thread we start a fresh one in this thread.
    """
    try:
        running = asyncio.get_running_loop()
    except RuntimeError:
        running = None
    if running is None:
        return asyncio.run(coro)
    new_loop = asyncio.new_event_loop()
    try:
        return new_loop.run_until_complete(coro)
    finally:
        new_loop.close()
