"""Payload extraction helpers for the Planner executor."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from a2a_research.a2a.proto import get_data_part, get_text_part

if TYPE_CHECKING:
    from a2a.server.agent_execution import RequestContext

__all__ = ["extract_payload", "extract_query"]


def extract_query(context: RequestContext) -> str:
    payload = extract_payload(context)
    query = payload.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    if context.message is None:
        return ""
    text_parts: list[str] = []
    for part in context.message.parts:
        part_data = get_data_part(part)
        if isinstance(part_data, dict):
            query = part_data.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        part_text = get_text_part(part)
        if part_text and part_text.strip():
            text_parts.append(part_text.strip())
    joined = "\n".join(text_parts).strip()
    try:
        data = json.loads(joined) if joined else None
    except (ValueError, TypeError):
        data = None
    if isinstance(data, dict) and isinstance(data.get("query"), str):
        return str(data["query"]).strip()
    return joined


def extract_payload(context: RequestContext) -> dict[str, object]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        payload = get_data_part(part)
        if isinstance(payload, dict):
            return payload
    return {}
