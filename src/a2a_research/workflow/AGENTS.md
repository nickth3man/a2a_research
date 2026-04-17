# WORKFLOW KNOWLEDGE BASE

## OVERVIEW
Top-level orchestrator for the 5-agent A2A web research pipeline. Drives:
Planner → FactChecker (which internally loops Searcher + Reader) → Synthesizer,
all via in-process `a2a-sdk` dispatch through `a2a_research.a2a.A2AClient`.

## STRUCTURE
```text
workflow/
├── __init__.py      # run_research / run_research_async / run_research_sync
├── __main__.py      # CLI: python -m a2a_research.workflow "query"
└── coordinator.py   # _drive() runs Planner -> FactChecker -> Synthesizer
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Public import | `__init__.py` | `run_research_sync` for blocking callers |
| Pipeline steps | `coordinator.py::_drive` | Planner → FactChecker → Synthesizer |
| FactChecker failure handling | `coordinator.py::_task_failed` + `_error_report` | Skips Synthesizer and writes an explicit `final_report` when search/read failed |
| Timeout behavior | `run_research_async` | `asyncio.wait_for(timeout=settings.workflow_timeout)` marks running agents FAILED |
| CLI smoke test | `__main__.py` | Prints report to stdout, per-agent summary to stderr |

## CONVENTIONS
- The Synthesizer is **never** called when the FactChecker's Task is
  `TaskState.failed` or its result has `search_exhausted=True`. Instead the
  coordinator writes a structured `final_report` naming the exact provider
  failures (Tavily disabled, DDG rate-limited, etc.).
- Use `_payload(task)` to extract the single DataPart from an A2A Task.
- Agent status transitions must go through `_set_status` so the Mesop UI
  timeline stays in sync.
- Timeout path: `_mark_running_failed` converts RUNNING → FAILED on abort.

## ANTI-PATTERNS
- Do not call `run_research_sync` from inside a running event loop (it raises).
- Do not let the Synthesizer run on empty evidence — that is exactly the
  behavior this layer exists to prevent.
- Do not attach progress reporters to A2A payloads; payloads are serialized
  through `a2a.types.DataPart` and arbitrary objects break round-trips.

## EDGE NOTES
- `__main__.py` is a read-only CLI; it does not persist Task state to disk.
- `run_research` is a legacy alias for `run_research_sync`.
