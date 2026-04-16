"""Input-sanitisation helpers used before interpolating user text into prompts."""

from __future__ import annotations

from a2a_research.app_logging import get_logger

logger = get_logger(__name__)

MAX_QUERY_CHARS = 10000


def sanitize_query(query: str) -> str:
    """Trim, collapse whitespace, and bound length of a user query."""
    query = query.strip()
    query = " ".join(query.split())
    if len(query) > MAX_QUERY_CHARS:
        logger.warning("Query truncated from %d to %d characters", len(query), MAX_QUERY_CHARS)
        return query[:MAX_QUERY_CHARS]
    return query
