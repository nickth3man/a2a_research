"""Tests for core.utils.json_utils.parse_json_safely."""

from __future__ import annotations

from core.utils.json_utils import parse_json_safely


def test_fenced_json_block() -> None:
    s = '```json\n{"x": 1, "y": 2}\n```'
    assert parse_json_safely(s) == {"x": 1, "y": 2}


def test_json_embedded_in_prose() -> None:
    s = 'Prefix text {"embedded": true} suffix'
    assert parse_json_safely(s) == {"embedded": True}


def test_decode_error_returns_empty_dict() -> None:
    assert parse_json_safely("not json") == {}


def test_top_level_list_returns_empty_dict() -> None:
    assert parse_json_safely('["a", "b"]') == {}
