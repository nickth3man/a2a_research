"""Tests for core.utils.timing."""

from __future__ import annotations

from core.utils.timing import perf_counter


class TestPerfCounter:
    def test_returns_float(self) -> None:
        result = perf_counter()
        assert isinstance(result, float)
        assert result > 0.0

    def test_monotonic_increasing(self) -> None:
        t1 = perf_counter()
        t2 = perf_counter()
        assert t2 >= t1
