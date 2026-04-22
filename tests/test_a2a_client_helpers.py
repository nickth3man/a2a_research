"""Tests for a2a_research.a2a.client_helpers."""

from __future__ import annotations

import json

from a2a.types import Artifact, Task

from a2a_research.a2a.client_helpers import (
    _payload_preview,
    build_message,
    extract_data_payload_or_warn,
    extract_data_payloads,
    extract_text,
)
from a2a_research.a2a.proto import (
    make_data_part,
    make_message,
    make_text_part,
    new_task,
)


def _make_task_with_artifact(parts) -> Task:
    """Helper: wrap parts in an Artifact and attach to a Task."""
    msg = make_message(task_id="t1", context_id="c1")
    task = new_task(msg)
    artifact = Artifact(
        artifact_id="art-1",
        name="out",
        parts=parts,
    )
    task.artifacts.append(artifact)
    return task


class TestExtractDataPayloads:
    def test_empty_task_no_artifacts(self) -> None:
        msg = make_message()
        task = new_task(msg)
        assert extract_data_payloads(task) == []

    def test_message_with_data_part(self) -> None:
        msg = make_message(data={"key": "val"})
        payloads = extract_data_payloads(msg)
        assert payloads == [{"key": "val"}]

    def test_message_with_text_part_only(self) -> None:
        msg = make_message(text="hello")
        assert extract_data_payloads(msg) == []

    def test_task_with_data_artifact(self) -> None:
        task = _make_task_with_artifact([make_data_part({"x": 1})])
        payloads = extract_data_payloads(task)
        assert payloads == [{"x": 1}]

    def test_task_with_multiple_data_parts(self) -> None:
        task = _make_task_with_artifact([
            make_data_part({"a": 1}),
            make_data_part({"b": 2}),
        ])
        payloads = extract_data_payloads(task)
        assert {"a": 1} in payloads
        assert {"b": 2} in payloads

    def test_message_with_multiple_data_parts(self) -> None:
        msg = make_message(data={"first": True})
        # Append a second data part manually
        msg.parts.append(make_data_part({"second": True}))
        payloads = extract_data_payloads(msg)
        assert len(payloads) == 2


class TestExtractText:
    def test_message_with_text(self) -> None:
        msg = make_message(text="hello world")
        assert extract_text(msg) == "hello world"

    def test_message_with_data_only(self) -> None:
        msg = make_message(data={"k": "v"})
        assert extract_text(msg) == ""

    def test_task_with_text_artifact(self) -> None:
        task = _make_task_with_artifact([make_text_part("artifact text")])
        assert extract_text(task) == "artifact text"

    def test_task_no_artifacts(self) -> None:
        msg = make_message()
        task = new_task(msg)
        assert extract_text(task) == ""

    def test_multiple_text_parts_joined_by_newline(self) -> None:
        task = _make_task_with_artifact([
            make_text_part("line1"),
            make_text_part("line2"),
        ])
        result = extract_text(task)
        assert "line1" in result
        assert "line2" in result
        assert "\n" in result


class TestExtractDataPayloadOrWarn:
    def test_empty_returns_empty_dict(self) -> None:
        msg = make_message(text="no data")
        result = extract_data_payload_or_warn(msg)
        assert result == {}

    def test_single_payload_returned_directly(self) -> None:
        msg = make_message(data={"answer": 42})
        result = extract_data_payload_or_warn(msg)
        assert result == {"answer": 42}

    def test_multiple_payloads_merged(self) -> None:
        msg = make_message(data={"a": 1})
        msg.parts.append(make_data_part({"b": 2}))
        result = extract_data_payload_or_warn(msg)
        assert result["a"] == 1
        assert result["b"] == 2

    def test_multiple_payloads_later_key_wins(self) -> None:
        msg = make_message(data={"key": "first"})
        msg.parts.append(make_data_part({"key": "second"}))
        result = extract_data_payload_or_warn(msg)
        assert result["key"] == "second"

    def test_task_with_single_artifact(self) -> None:
        task = _make_task_with_artifact([make_data_part({"result": "ok"})])
        result = extract_data_payload_or_warn(task)
        assert result == {"result": "ok"}

    def test_task_no_artifacts_returns_empty(self) -> None:
        msg = make_message()
        task = new_task(msg)
        result = extract_data_payload_or_warn(task)
        assert result == {}


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
        # Should not raise, uses default=str
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
