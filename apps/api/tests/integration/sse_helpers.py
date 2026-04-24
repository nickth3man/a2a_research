"""SSE parsing helpers for integration tests.

Provides utilities for consuming and asserting against Server-Sent Events
streams emitted by the FastAPI gateway.

Usage::

    from tests.integration.sse_helpers import collect_sse_events, assert_sse_event

    # Collect all events from a streaming response
    events = collect_sse_events(response)
    assert len(events) >= 1

    # Assert a specific event
    assert_sse_event(events[0], expected_event="result", expected_data={"session_id": "..."})
"""

from __future__ import annotations

import json
from typing import Any

import httpx


def collect_sse_events(
    response: httpx.Response,
    max_events: int = 10,
) -> list[tuple[str, dict[str, Any]]]:
    """Parse SSE stream from an httpx response into a list of (event, data) tuples.

    Handles the standard SSE format emitted by :func:`api_serializers.sse`::

        event: <event-name>\\n
        data: <json-payload>\\n
        \\n

    Args:
        response: An httpx response with ``media_type="text/event-stream"``.
        max_events: Safety cap — stop after collecting this many events.

    Returns:
        List of ``(event_name, parsed_data_dict)`` tuples.

    Example::

        with client.stream("GET", "/api/research/abc123/stream") as resp:
            events = collect_sse_events(resp)
        assert events[-1][0] == "result"
    """
    events: list[tuple[str, dict[str, Any]]] = []
    current_event: str | None = None
    current_data: str | None = None

    for line in response.iter_lines():
        line = line.strip()
        if line.startswith("event:"):
            current_event = line[len("event:") :].strip()
        elif line.startswith("data:"):
            current_data = line[len("data:") :].strip()
        elif line == "" and current_event is not None and current_data is not None:
            try:
                parsed = json.loads(current_data)
            except json.JSONDecodeError:
                parsed = {"_raw": current_data}
            events.append((current_event, parsed))
            current_event = None
            current_data = None
            if len(events) >= max_events:
                break

    # Flush any trailing event (no trailing blank line)
    if current_event is not None and current_data is not None and len(events) < max_events:
        try:
            parsed = json.loads(current_data)
        except json.JSONDecodeError:
            parsed = {"_raw": current_data}
        events.append((current_event, parsed))

    return events


def assert_sse_event(
    event: tuple[str, dict[str, Any]],
    *,
    expected_event: str | None = None,
    expected_data: dict[str, Any] | None = None,
) -> None:
    """Assert that an SSE event tuple matches expectations.

    Args:
        event: A ``(event_name, data_dict)`` tuple from :func:`collect_sse_events`.
        expected_event: If provided, assert the event name matches exactly.
        expected_data: If provided, assert the data dict is a superset of these keys.

    Raises:
        AssertionError: If the event does not match expectations.

    Example::

        events = collect_sse_events(response)
        assert_sse_event(
            events[-1],
            expected_event="result",
            expected_data={"session_id": "abc123"},
        )
    """
    event_name, data = event

    if expected_event is not None:
        assert event_name == expected_event, (
            f"Expected SSE event '{expected_event}', got '{event_name}'"
        )

    if expected_data is not None:
        for key, value in expected_data.items():
            assert key in data, (
                f"Expected key '{key}' in SSE data, got keys: {list(data.keys())}"
            )
            if value is not None:
                assert data[key] == value, (
                    f"Expected data['{key}'] == {value!r}, got {data[key]!r}"
                )


def stream_with_timeout(
    client: httpx.Client,
    method: str,
    url: str,
    *,
    max_events: int = 10,
    timeout_sec: float = 5.0,
    **kwargs: Any,
) -> list[tuple[str, dict[str, Any]]]:
    """Wrapper around httpx streaming with event cap and timeout.

    Opens a streaming connection, collects SSE events up to ``max_events``,
    and returns them as parsed tuples.  Designed for sync
    :class:`httpx.Client`; for async usage, call ``collect_sse_events``
    directly inside an ``async with client.stream(...)`` block.

    Args:
        client: A sync :class:`httpx.Client` instance.
        method: HTTP method (e.g. ``"GET"``).
        url: URL path to stream from.
        max_events: Maximum number of SSE events to collect.
        timeout_sec: Timeout in seconds for the streaming request.
        **kwargs: Additional keyword arguments forwarded to ``client.stream()``.

    Returns:
        List of ``(event_name, data_dict)`` tuples.

    Example::

        from httpx import Client

        with Client(transport=ASGITransport(app=app), base_url="http://test") as c:
            events = stream_with_timeout(c, "GET", "/api/research/abc/stream")
        assert events[-1][0] == "result"
    """
    kwargs.setdefault("timeout", timeout_sec)
    with client.stream(method, url, **kwargs) as response:
        return collect_sse_events(response, max_events=max_events)
