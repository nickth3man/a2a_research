"""Tests for client_helpers payload preview and build_message."""

from __future__ import annotations

import json

from a2a_research.backend.core.a2a.client_helpers import (
    _payload_preview,
    build_message,
)


class TestPayloadPreview:
    def test_none_returns_empty(self) -> None:
        keys, size, preview = _payload_preview(None)
        assert keys == []
        assert size == 0
        assert preview == ""

    def test_empty_dict_returns_empty(self) -> None:
        keys, size, preview = _payload_preview({})
        assert keys == []
        assert size == 0
        assert preview == ""

    def test_keys_are_sorted(self) -> None:
        payload = {"z": 1, "a": 2, "m": 3}
        keys, _, _ = _payload_preview(payload)
        assert keys == ["a", "m", "z"]

    def test_size_is_byte_count(self) -> None:
        payload = {"key": "value"}
        _, size, _preview = _payload_preview(payload)
        expected = len(
            json.dumps(payload, default=str, indent=2, sort_keys=True).encode(
                "utf-8"
            )
        )
        assert size == expected

    def test_preview_is_json_string(self) -> None:
        payload = {"hello": "world"}
        _, _, preview = _payload_preview(payload)
        parsed = json.loads(preview)
        assert parsed == {"hello": "world"}

    def test_non_serializable_uses_str_default(self) -> None:
        from datetime import datetime

        dt = datetime(2024, 1, 1, 0, 0, 0)
        payload = {"ts": dt}
        _keys, size, preview = _payload_preview(payload)
        assert size > 0
        parsed = json.loads(preview)
        assert "ts" in parsed


class TestBuildMessage:
    def test_returns_message_with_text(self) -> None:
        msg = build_message(text="hello")
        texts = [p.text for p in msg.parts if p.text]
        assert "hello" in texts

    def test_returns_message_with_data(self) -> None:
        msg = build_message(data={"k": "v"})
        data_parts = [p for p in msg.parts if p.HasField("data")]
        assert len(data_parts) == 1

    def test_task_id_and_context_id(self) -> None:
        msg = build_message(task_id="t1", context_id="c1")
        assert msg.task_id == "t1"
        assert msg.context_id == "c1"
