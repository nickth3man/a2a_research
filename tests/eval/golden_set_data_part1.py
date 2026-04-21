"""Golden query set data (part 1: factual, subjective, unanswerable)."""

from __future__ import annotations

from tests.eval.golden_set import EvalQuery
from tests.eval.golden_set_data_factual import _GOLDEN_SET_FACTUAL
from tests.eval.golden_set_data_subjective import _GOLDEN_SET_SUBJECTIVE
from tests.eval.golden_set_data_unanswerable import _GOLDEN_SET_UNANSWERABLE

_GOLDEN_SET_PART1: list[EvalQuery] = (
    _GOLDEN_SET_FACTUAL
    + _GOLDEN_SET_SUBJECTIVE
    + _GOLDEN_SET_UNANSWERABLE
)
