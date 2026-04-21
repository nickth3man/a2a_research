"""Payload/query extraction helpers for the Clarifier agent."""

from __future__ import annotations

import json
from typing import Any

from a2a.server.agent_execution import RequestContext
from a2a_research.a2a.proto import get_data_part, get_text_part


def _extract_query(context: RequestContext, payload: dict[str, Any]) -> str:
    query = payload.get("query")
    if isinstance(query, str) and query.strip():
        return query.strip()
    if context.message is None:
        return ""
    text_parts: list[str] = []
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            query = data_part.get("query")
            if isinstance(query, str) and query.strip():
                return query.strip()
        text_part = get_text_part(part)
        if text_part and text_part.strip():
            text_parts.append(text_part.strip())
    joined = "\n".join(text_parts).strip()
    try:
        data = json.loads(joined) if joined else None
    except (ValueError, TypeError):
        data = None
    if isinstance(data, dict) and isinstance(data.get("query"), str):
        return str(data["query"]).strip()
    return joined


def _extract_payload(context: RequestContext) -> dict[str, object]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
    return {}
