# WORKFLOW KNOWLEDGE BASE

## OVERVIEW
PocketFlow runtime for the research pipeline. This package owns graph construction, node execution, sync/async entrypoints, and policy scaffolding.

## STRUCTURE
```text
workflow/
├── __init__.py      # public workflow exports
├── builder.py       # build ordered role pipeline into AsyncFlow
├── nodes.py         # ActorNode wrapper over A2A dispatch
├── entrypoints.py   # async/sync runtime entrypoints + timeout handling
├── coordinator.py   # legacy linear coordinator surface
├── adapter.py       # SyncWorkflowAdapter invoke()/ainvoke()
└── policy.py        # ordering/policy primitives
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Stable public import | `__init__.py` | `run_research_sync` lives here |
| Assemble flow from roles | `builder.py` | `build_workflow`, `get_workflow` |
| Understand node/session contract | `nodes.py` | requires shared `session` key |
| Run workflow async | `entrypoints.py` | primary runtime path |
| Use sync adapter object | `adapter.py` | `invoke` wraps `asyncio.run` |
| Older coordinator behavior | `coordinator.py` | keep for compatibility; prefer generic builder path |

## CONVENTIONS
- Prefer `run_research_sync` for blocking callers and `run_workflow_async` for async callers.
- Shared workflow state must include `session`; progress support is threaded through `progress_reporter`.
- Builder rejects empty role lists; role ordering is explicit, not inferred.
- Timeout behavior is part of the contract: long-running flows return a partial session with running agents marked failed.

## ANTI-PATTERNS
- Do not call `run_workflow_sync` or `SyncWorkflowAdapter.invoke()` from inside an existing event loop.
- Do not bypass `ActorNode` and call handlers directly if you still expect A2A/progress/session semantics.
- Do not put arbitrary objects into message payloads; progress reporter is attached as a private attribute specifically because payloads are serialized.
- Do not add a role to the flow without matching the four-file registration contract described in the root AGENTS.

## EDGE NOTES
- `coordinator.py` is a compatibility surface; the generic `builder.py` + `entrypoints.py` path is the main architecture.
- `helpers/__init__.py` contains report-building PocketFlow nodes; reporting logic is not fully isolated inside `workflow/`.
