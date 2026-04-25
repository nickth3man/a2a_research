"""Shared web research tools used by Searcher and Reader agents.

- :func:`web_search` — parallel Tavily + Brave + DuckDuckGo search, merged by
  URL.
- :func:`fetch_and_extract` — trafilatura-based fetch + main-text extraction.
- :class:`WebHit`, :class:`PageContent` — Pydantic DTOs exchanged via A2A.
"""

from __future__ import annotations

from tools.fetch import (
    PageContent,
    fetch_and_extract,
    fetch_many,
)
from tools.search import web_search
from tools.search_models import SearchResult, WebHit

__all__ = [
    "PageContent",
    "SearchResult",
    "WebHit",
    "fetch_and_extract",
    "fetch_many",
    "web_search",
]
