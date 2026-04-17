"""Low-level JSON parsing utilities with no internal dependencies.

Kept at the package root so that both ``providers`` and agent-level helpers
can import it without creating circular dependencies.
"""

from __future__ import annotations

import json
import re
from typing import Any, cast


def parse_json_safely(content: str) -> dict[str, Any]:
    """Extract and parse a JSON object from *content*, returning ``{}`` on failure.

    Handles fenced code blocks (````json ... ````), bare JSON objects, and
    strings that contain a JSON object embedded in surrounding prose.
    """
    content = content.strip()
    fence_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```")
    match = fence_pattern.search(content)
    if match:
        content = match.group(1)
    else:
        json_start = content.find("{")
        json_end = content.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            content = content[json_start:json_end]
    try:
        return cast("dict[str, Any]", json.loads(content))
    except json.JSONDecodeError:
        return {}
