"""Web search provider implementations."""

from a2a_research.backend.tools.search_brave import search_brave
from a2a_research.backend.tools.search_ddg import search_ddg
from a2a_research.backend.tools.search_merge import merge_hits_by_url
from a2a_research.backend.tools.search_tavily import search_tavily

__all__ = [
    "merge_hits_by_url",
    "search_brave",
    "search_ddg",
    "search_tavily",
]
