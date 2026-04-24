"""Tests for a2a_research.a2a.proto."""

from __future__ import annotations

from datetime import date, datetime

from a2a.types import Part, Role

from a2a_research.backend.core.a2a.proto import (
    ROLE_AGENT,
    ROLE_USER,
    _serialize_for_proto,
    get_data_part,
    get_text_part,
    make_data_part,
    make_text_part,
)


class TestRoleConstants:
    def test_role_user_is_role_user(self) -> None:
        assert ROLE_USER == Role.ROLE_USER

    def test_role_agent_is_role_agent(self) -> None:
        assert ROLE_AGENT == Role.ROLE_AGENT


class TestSerializeForProto:
    def test_datetime_to_isoformat(self) -> None:
        dt = datetime(2024, 1, 15, 12, 30, 0)
        result = _serialize_for_proto(dt)
        assert result == "2024-01-15T12:30:00"

    def test_date_to_isoformat(self) -> None:
        d = date(2024, 6, 1)
        result = _serialize_for_proto(d)
        assert result == "2024-06-01"

    def test_dict_recursion(self) -> None:
        dt = datetime(2024, 1, 1, 0, 0, 0)
        result = _serialize_for_proto({"ts": dt, "val": 42})
        assert result == {"ts": "2024-01-01T00:00:00", "val": 42}

    def test_list_recursion(self) -> None:
        d = date(2025, 3, 10)
        result = _serialize_for_proto([d, "plain", 1])
        assert result == ["2025-03-10", "plain", 1]

    def test_passthrough_string(self) -> None:
        assert _serialize_for_proto("hello") == "hello"

    def test_passthrough_int(self) -> None:
        assert _serialize_for_proto(99) == 99

    def test_passthrough_none(self) -> None:
        assert _serialize_for_proto(None) is None

    def test_nested_dict_in_list(self) -> None:
        dt = datetime(2024, 7, 4, 8, 0, 0)
        result = _serialize_for_proto([{"ts": dt}])
        assert result == [{"ts": "2024-07-04T08:00:00"}]


class TestMakeTextPart:
    def test_returns_part(self) -> None:
        part = make_text_part("hello")
        assert isinstance(part, Part)

    def test_text_field_set(self) -> None:
        part = make_text_part("world")
        assert part.text == "world"

    def test_empty_text(self) -> None:
        part = make_text_part("")
        assert part.text == ""


class TestMakeDataPart:
    def test_returns_part(self) -> None:
        part = make_data_part({"key": "value"})
        assert isinstance(part, Part)

    def test_has_data_field(self) -> None:
        part = make_data_part({"x": 1})
        assert part.HasField("data")

    def test_does_not_have_text_field(self) -> None:
        part = make_data_part({"x": 1})
        assert not part.text


class TestGetTextPart:
    def test_returns_text_for_text_part(self) -> None:
        part = make_text_part("hello")
        assert get_text_part(part) == "hello"

    def test_returns_none_for_data_part(self) -> None:
        part = make_data_part({"x": 1})
        assert get_text_part(part) is None

    def test_returns_none_for_empty_text_part(self) -> None:
        part = make_text_part("")
        assert get_text_part(part) is None


class TestGetDataPart:
    def test_returns_dict_for_data_part(self) -> None:
        part = make_data_part({"foo": "bar"})
        result = get_data_part(part)
        assert isinstance(result, dict)
        assert result == {"foo": "bar"}

    def test_returns_none_for_text_part(self) -> None:
        part = make_text_part("text")
        assert get_data_part(part) is None

    def test_nested_data(self) -> None:
        part = make_data_part({"a": {"b": 1}})
        result = get_data_part(part)
        assert result == {"a": {"b": 1}}
