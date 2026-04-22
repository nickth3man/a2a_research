"""smolagents ``Tool`` subclass wrapping
:func:`a2a_research.tools.fetch.fetch_and_extract`.
"""

from __future__ import annotations

import asyncio
from typing import Any, ClassVar, cast

from smolagents import Tool

from a2a_research.tools import fetch_and_extract

__all__ = ["FetchAndExtractTool"]


class FetchAndExtractTool(Tool):
    name = "fetch_and_extract"
    description = (
        "Fetch a URL and extract its main content as markdown using"
        " trafilatura. Returns {url, title, markdown, word_count, error}."
    )
    inputs: ClassVar[dict[str, Any]] = {
        # smolagents Tool requires this as a class attribute
        "url": {
            "type": "string",
            "description": "Absolute http(s) URL to fetch and extract.",
        },
    }
    output_type = "object"

    def forward(self, url: str) -> dict[str, Any]:
        page = _run(fetch_and_extract(url))
        return cast("dict[str, Any]", page.model_dump(mode="json"))


def _run(coro: Any) -> Any:
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
