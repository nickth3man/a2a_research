# Evaluation and Regression Tests

This directory contains the golden sets, scoring logic, and regression harness for evaluating the A2A research pipeline.

## What lives here

| File | Purpose |
|------|---------|
| `golden_set.py` | Pydantic models plus category/id helpers for golden queries |
| `golden_set_data.py` | Immutable combined golden set (20 total queries) |
| `golden_set_data_factual.py` | Factual benchmark queries |
| `golden_set_data_subjective.py` | Subjective benchmark queries |
| `golden_set_data_unanswerable.py` | Unanswerable benchmark queries |
| `golden_set_data_part1.py` / `golden_set_data_part2.py` | Split golden-set bundles used to assemble the full set |
| `scoring_metrics.py` | Individual metric implementations |
| `scoring.py` | Dataclass wrapper that runs the full scoring rubric |
| `regression_mock.py` | Deterministic mock pipeline used by the regression harness |
| `regression_report.py` | Markdown report generation and baseline comparison helpers |
| `regression_helpers.py` | Backward-compatible re-exports of runner/report helpers |
| `regression_runner.py` | CLI entry point that runs eval, writes JSON, and emits reports |
| `test_eval_*.py` | Tests for golden data, scoring, and regression behavior |

## Golden sets

The golden set is a fixed benchmark of 20 queries across five categories:

- `factual`
- `subjective`
- `unanswerable`
- `sensitive`
- `ambiguous`

Each `EvalQuery` records:

- stable `id`
- input `text`
- `category`
- expected claim and citation counts
- expected verdicts (`ExpectedVerdict`)
- optional notes

`golden_set.py` exposes:

- `GOLDEN_SET`
- `get_by_category(category)`
- `get_by_id(query_id)`

## Scoring

`scoring_metrics.py` implements the individual metrics:

- `score_claim_recall`
- `score_citation_accuracy`
- `score_independence`
- `score_adversary_catch_rate`
- `compute_composite_score`

`scoring.py` wraps those metrics in `EvalScores` and `score_run(...)`.

Default composite weights:

- claim recall: `0.35`
- citation accuracy: `0.35`
- independence: `0.15`
- adversary catch rate: `0.15`

## Regression harness

`regression_runner.py` runs the full golden set through the mock pipeline, scores each query, aggregates the results, and optionally compares them to a baseline JSON file.

`regression_report.py` turns the run output into markdown and flags regressions when a metric drops by more than 5% from baseline.

`regression_mock.py` keeps the harness deterministic so tests stay fast and repeatable.

## Running

```bash
make test
```

Direct runner usage:

```bash
python -m tests.eval.regression_runner
python -m tests.eval.regression_runner --baseline path/to/baseline.json --output report.md
```

## Tests

- `test_eval_harness.py` covers golden-set shape and helpers
- `test_eval_scoring.py` covers metric behavior
- `test_eval_scoring_extra.py` covers composite scoring and `score_run`
- `test_eval_regression.py` covers the mock pipeline, baseline comparison, report generation, and CLI behavior
