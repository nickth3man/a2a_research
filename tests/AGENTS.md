# TESTS KNOWLEDGE BASE

## OVERVIEW
Flat pytest suite with strong workflow and UI coverage. Tests assume zero live network/API access and rely on aggressive singleton reset between cases.

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Shared fixtures | `conftest.py` | Mesop stubs + global singleton reset |
| Workflow end-to-end | `test_workflow.py` | primary pipeline behavior |
| Workflow edge cases | `test_workflow_runtime.py`, `test_workflow_entrypoints_extra.py`, `test_workflow_units_extra.py`, `test_workflow_package_surface.py` | extend nearest existing file |
| UI behavior | `test_ui_*.py` files | page, components, theme, session-state coverage |
| Provider behavior | `test_providers.py` | SDK mocking and error mapping |
| RAG/A2A behavior | `test_rag_and_a2a.py` | corpus, retrieval, dispatch |

## CONVENTIONS
- Tests run with pytest defaults from `pyproject.toml`: `-n auto --cov=src/a2a_research --cov-report=term-missing` and warnings-as-errors.
- `conftest.py::_reset_global_singletons` is `autouse=True`; if you add a new module-level cache/singleton, extend that fixture.
- UI tests stub Mesop runtime instead of running a live server.
- Unit tests mock `_call_llm`, provider SDK loading, and Chroma interactions; no API key is required.

## ANTI-PATTERNS
- Do not add tests that depend on real provider credentials or network access.
- Do not create a new top-level test file when an existing domain file already matches the subject.
- Do not bypass the Mesop runtime stubs when testing components/pages; those tests will fail for the wrong reason.
- Do not forget that warnings fail the suite.

## USEFUL INVOCATIONS
```bash
uv run pytest
uv run pytest tests/test_workflow.py
uv run pytest tests/test_workflow.py::test_name -v
```

## HOTSPOTS
- UI coverage is intentionally split across multiple focused files; keep that separation.
- Workflow tests often patch a sequence of LLM responses to simulate the four-agent run end-to-end.
