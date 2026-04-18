# Development

## Setup

```bash
make install
make dev
```

## Core commands

```bash
make check
make test
make serve-all
make mesop
```

## Local workflow

### Full app

Terminal A:

```bash
make serve-all
```

Terminal B:

```bash
make mesop
```

### Single agent

```bash
make serve-planner
make serve-searcher
make serve-reader
make serve-fact-checker
make serve-synthesizer
```

## Adding or changing an agent

1. define or update the agent executor in `agents/.../main.py`
2. keep the A2A artifact shape stable
3. update the role card in `agents/.../card.py`
4. expose `build_http_app()` and `__main__.py`
5. add or update:
   - unit tests
   - HTTP contract tests
   - integration tests if behavior crosses service boundaries

## Debugging tips

- use `LOG_LEVEL=DEBUG` for noisy traces
- test one agent at a time with the `make serve-<name>` targets
- if an HTTP contract test fails, verify the app via `A2AStarletteApplication` + `ASGITransport`
- if the UI looks stale, inspect the progress queue events first

## Test structure

- `tests/test_agent_*.py` — executor-level unit tests
- `tests/test_agent_*_http.py` — HTTP contract tests
- `tests/test_workflow_integration.py` — full pipeline integration
- `tests/test_progress.py` — progress drain/bus behavior

## Public API stability

These imports must continue to work:

```python
from a2a_research.workflow import run_research_sync, run_research_async
```
