"""Golden query set data for evaluating the multi-agent research pipeline."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery
from tests.eval.golden_set_data_part1 import _GOLDEN_SET_PART1
from tests.eval.golden_set_data_part2 import _GOLDEN_SET_PART2

_GOLDEN_SET: list[EvalQuery] = _GOLDEN_SET_PART1 + _GOLDEN_SET_PART2

GOLDEN_SET: tuple[EvalQuery, ...] = tuple(_GOLDEN_SET)
"""Immutable tuple of all 20 golden-set queries."""
