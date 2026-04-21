"""Tests for parse_structured_response."""

from __future__ import annotations

from pydantic import BaseModel

from a2a_research.llm.providers import parse_structured_response


class _FakeSchema(BaseModel):
    value: str


class TestParseStructuredResponse:
    def test_parse_structured_response_returns_none_for_invalid_json(
        self,
    ) -> None:
        assert parse_structured_response("not json", _FakeSchema) is None

    def test_parse_structured_response_returns_none_for_empty_string(
        self,
    ) -> None:
        assert parse_structured_response("", _FakeSchema) is None

    def test_parse_structured_response_returns_none_for_json_that_fails_schema(
        self,
    ) -> None:
        class StrictSchema(BaseModel):
            value: int

        assert (
            parse_structured_response('{"value": "not-an-int"}', StrictSchema)
            is None
        )

    def test_parse_structured_response_uses_model_validate(self) -> None:
        class SimpleSchema(BaseModel):
            value: int

        result = parse_structured_response('{"value": 42}', SimpleSchema)
        assert result is not None
        assert result.value == 42
