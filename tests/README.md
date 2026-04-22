# Test Suite

Pytest suite for the `a2a_research` pipeline: protocol helpers, agents, models,
providers, tools, UI, workflow, logging, and live-search integration.

## Layout

| Area | Files |
|------|-------|
| A2A protocol/helpers | `test_a2a_*.py`, `test_fact_checker_init.py` |
| Agents | `test_agent_*.py` |
| Models | `test_models_*.py` |
| Providers | `test_providers_*.py` |
| Settings | `test_settings_*.py` |
| Tools | `test_tools_*.py` |
| UI | `test_ui_*.py`, `test_app_logging.py` |
| Workflow | `test_workflow_*.py`, `test_progress.py` |
| Live network tests | `test_brave_live_*.py`, `test_tavily_live_*.py` |
| Utility/guardrail tests | `test_citation_sanitize.py`, `test_file_length.py`, `test_budget_*.py` |

`test_models_workflow.py` is a compatibility shim; the real model coverage is
split across the domain-specific `test_models_*.py` files.

## Shared helpers

| File | Purpose |
|------|---------|
| `conftest.py` | Loads `.env`, seeds test credentials, resets singletons, stubs Mesop runtime |
| `http_harness.py` | In-memory ASGI transport + A2A SDK client helpers for service tests |
| `ui_app_helpers.py` | Shared Mesop app state builders and submit-drain helper |
| `workflow_integration_helpers.py` | In-memory multi-service wiring and success-path monkeypatches |
| `brave_live_helpers.py` | Brave live-test skip logic and hit-text matching helpers |
| `__init__.py` | Marks `tests/` as a package |

## Naming rules

- `test_<area>_<thing>.py` for test modules.
- `Test<Thing>` for classes, `test_<behavior>` for methods/functions.
- Helper modules end in `_helpers.py`; shared harness code lives there.
- Live tests keep the `_live_` prefix and `@pytest.mark.integration`.
- HTTP contract tests use the `_http` suffix.
- Keep files focused; `test_file_length.py` enforces size/line-width guardrails.

## Running tests

```bash
make test             # Full suite, skips live API tests
make test-live-brave  # Brave live tests (requires BRAVE_LIVE=1 + BRAVE_API_KEY)
make test-live-tavily # Tavily live tests (requires TAVILY_LIVE=1 + API keys)
make test-live        # All live API tests
make watch            # Pytest watch mode
make htmlcov          # HTML coverage report
make all              # Tests + lint/type checks for CI
```

## Notes

- Live tests are skipped unless the matching `*_LIVE` flag is set.
- `pytest` is configured for async tests and parallel execution via `xdist`.
- Keep assertions deterministic; most external dependencies are mocked, with
  real network coverage isolated to the live test files.
