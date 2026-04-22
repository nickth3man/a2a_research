"""Utility functions for validation and type coercion."""

from __future__ import annotations

from typing import Any


def to_str_list(value: Any) -> list[str]:
    """Convert a value to a list of strings."""
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


def to_float(value: Any, default: float) -> float:
    """Convert a value to a float, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


__all__ = ["to_float", "to_str_list"]
