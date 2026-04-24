"""Tests for validation utilities."""

from __future__ import annotations

import pytest

from a2a_research.backend.core.utils.validation import to_float, to_str_list


class TestToStrList:
    def test_empty_list_returns_empty(self):
        assert to_str_list([]) == []

    def test_list_of_strings_returns_same(self):
        assert to_str_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_list_with_integers_converts_to_strings(self):
        assert to_str_list([1, 2, 3]) == ["1", "2", "3"]

    def test_list_with_mixed_types_converts_to_strings(self):
        assert to_str_list(["a", 1, 2.5, True]) == ["a", "1", "2.5", "True"]

    def test_list_with_none_filters_none(self):
        assert to_str_list(["a", None, "b", None, "c"]) == ["a", "b", "c"]

    def test_none_input_returns_empty(self):
        assert to_str_list(None) == []

    def test_string_input_returns_empty(self):
        assert to_str_list("not a list") == []

    def test_dict_input_returns_empty(self):
        assert to_str_list({"key": "value"}) == []

    def test_integer_input_returns_empty(self):
        assert to_str_list(42) == []


class TestToFloat:
    def test_float_value_returns_float(self):
        assert to_float(3.14, 0.0) == 3.14

    def test_int_value_returns_float(self):
        assert to_float(42, 0.0) == 42.0

    def test_string_float_returns_float(self):
        assert to_float("2.5", 0.0) == 2.5

    def test_string_int_returns_float(self):
        assert to_float("10", 0.0) == 10.0

    def test_none_returns_default(self):
        assert to_float(None, 99.9) == 99.9

    def test_invalid_string_returns_default(self):
        assert to_float("not a number", -1.0) == -1.0

    def test_empty_string_returns_default(self):
        assert to_float("", 0.0) == 0.0

    def test_list_returns_default(self):
        assert to_float([1, 2, 3], 0.0) == 0.0

    def test_dict_returns_default(self):
        assert to_float({"a": 1}, 0.0) == 0.0

    def test_default_is_mandatory_positional(self):
        # Ensure default parameter is used correctly
        assert to_float("abc", 0.0) == 0.0
        assert to_float("abc", 100.0) == 100.0
