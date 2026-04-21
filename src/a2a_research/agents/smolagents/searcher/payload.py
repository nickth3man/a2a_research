"""Searcher payload helpers."""

from __future__ import annotations

import json
from typing import Any

from a2a.server.agent_execution import RequestContext

from a2a_research.a2a.proto import get_data_part, get_text_part


def _extract_payload(context: RequestContext) -> dict[str, object]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
        text_part = get_text_part(part)
        if text_part:
            try:
                data = json.loads(text_part)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return dict(data)
    return {}


def _coerce_str_list(raw: Any) -> list[str]:
    if isinstance(raw, str):
        return [raw] if raw.strip() else []
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return []
