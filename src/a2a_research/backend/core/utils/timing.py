"""Utility functions for timing."""

from __future__ import annotations

import time


def perf_counter() -> float:
    """Return the value (in fractional seconds) of a performance counter."""
    return time.perf_counter()


__all__ = ["perf_counter"]
