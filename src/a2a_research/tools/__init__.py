"""Shared web research tools used by Searcher and Reader agents.

- :func:`web_search` — parallel Tavily + Brave + DuckDuckGo search, merged by URL.
- :func:`fetch_and_extract` — trafilatura-based fetch + main-text extraction.
- :class:`WebHit`, :class:`PageContent` — Pydantic DTOs exchanged via A2A.
"""

from __future__ import annotations

from a2a_research.tools.fetch import PageContent, fetch_and_extract, fetch_many
from a2a_research.tools.search import SearchResult, WebHit, web_search

__all__ = [
    "PageContent",
    "SearchResult",
    "WebHit",
    "fetch_and_extract",
    "fetch_many",
    "web_search",
]
