# Workflow

Workflow orchestration for the A2A research pipeline.

This package contains two execution modes:

- **v1**: linear 5-agent coordinator flow
- **v2**: claim-centric workflow engine with iterative evidence loops

## Runnable entrypoints

- `python -m a2a_research.workflow "query"` — CLI wrapper that prints the final markdown report to stdout and per-agent status to stderr
- `a2a_research.backend.workflow.run_research_sync(query)` — legacy sync alias
- `a2a_research.backend.workflow.run_research_async(query)` — v1 async runner
- `a2a_research.backend.workflow.run_workflow_v2_sync(query)` — v2 sync runner
- `a2a_research.backend.workflow.run_workflow_v2_async(query)` — v2 async runner

## Module map

### Public API

- `__init__.py` — re-exports the workflow runners
- `__main__.py` — CLI entrypoint

### v1 coordinator flow

- `coordinator.py` — top-level v1 runner
- `coordinator_drive.py` — drives planner → searcher → reader → fact checker → synthesizer
- `coordinator_planner.py` — planner step
- `coordinator_searcher.py` — search step
- `coordinator_reader.py` — read/extract step
- `coordinator_fact_checker.py` — verification step
- `coordinator_synthesizer.py` — report synthesis step
- `coordinator_helpers.py` — shared status/report/coercion helpers

### v2 claim-centric engine

- `workflow_engine.py` — v2 runner and compatibility aliases
- `engine.py` — main v2 driver
- `engine_setup.py` — preprocess, clarify, plan
- `engine_loop.py` — iterative evidence loop
- `engine_gather.py` — search, rank, read, normalize
- `engine_verify.py` — verify plus adversary gate
- `engine_replan.py` — surgical replanning
- `engine_final.py` — synthesize, critique, postprocess
- `engine_provenance.py` — provenance updates for gathered evidence

### Shared workflow utilities

- `agents.py` — A2A agent execution helper
- `claims.py` — claim ordering and preprocessing abort logic
- `coerce.py` — payload-to-model coercion helpers
- `definitions.py` — agent registry, step indices, timeouts, budget config
- `provenance.py` — provenance node/edge helpers and ID builders
- `reports.py` — failure report builders
- `status.py` — agent status updates and progress emission

## Execution shape

### v1

`Planner → Searcher → Reader → FactChecker → Synthesizer`

### v2

`Preprocess → Clarify → Plan → iterative gather/verify/replan loop → Synthesize → Critique → Postprocess`

## Key concepts

- **Agent roles** are defined in `definitions.py` and include planner/searcher/reader/fact checker/synthesizer plus v2 roles like preprocessor, clarifier, ranker, deduplicator, adversary, critic, and postprocessor.
- **Status tracking** is stored on `ResearchSession.agent_results` and updated through `status.py` or coordinator helpers.
- **Provenance** is built as a node/edge tree linking claims, queries, hits, pages, passages, verdicts, and challenges.
- **Budgets and timeouts** are centralized in `definitions.py`.

## File purpose summary

| File | Purpose |
|------|---------|
| `__init__.py` | Public workflow exports |
| `__main__.py` | CLI runner |
| `agents.py` | Execute a single agent call |
| `claims.py` | Select unresolved claims and preprocessing abort checks |
| `coerce.py` | Convert raw agent payloads into typed models |
| `coordinator.py` | v1 synchronous/async workflow entrypoint |
| `coordinator_drive.py` | v1 orchestration chain |
| `coordinator_fact_checker.py` | v1 verification step |
| `coordinator_helpers.py` | v1 shared utilities |
| `coordinator_planner.py` | v1 planning step |
| `coordinator_reader.py` | v1 reading step |
| `coordinator_searcher.py` | v1 search step |
| `coordinator_synthesizer.py` | v1 synthesis step |
| `definitions.py` | Agent definitions, timeouts, budgets |
| `engine.py` | v2 main driver |
| `engine_final.py` | v2 final stages |
| `engine_gather.py` | v2 evidence gathering |
| `engine_loop.py` | v2 outer loop |
| `engine_provenance.py` | v2 provenance updates |
| `engine_replan.py` | v2 replanning |
| `engine_setup.py` | v2 setup stages |
| `engine_verify.py` | v2 verification/adversary stages |
| `provenance.py` | Provenance ID helpers |
| `reports.py` | Failure report helpers |
| `status.py` | Progress/status helpers |
| `workflow_engine.py` | v2 public workflow API |
