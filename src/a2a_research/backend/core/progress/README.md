# Progress Tracking

Real-time progress events for the research pipeline. This package emits structured updates that UI layers (like the Mesop frontend) consume to show live agent activity.

## Files

| File | Purpose |
|------|---------|
| `progress_types.py` | Core types: events, phases, granularity, queues, reporters, and text helpers |
| `progress_bus.py` | In-process registry (`Bus`) that maps session IDs to progress queues |
| `progress_emit_core.py` | Low-level `emit()` plus `emit_tool_call` and `emit_rate_limit` |
| `progress_emit_events.py` | `emit_handoff` and `emit_claim_verdict` for workflow transitions |
| `progress_emit_prompts.py` | `emit_prompt` and `emit_llm_response` for LLM visibility |
| `progress_emit.py` | Backward-compatible re-export of all emit functions |
| `progress_utils.py` | `create_progress_reporter` and `drain_progress_while_running` |
| `__init__.py` | Public API re-exports |

## Core Types

### `ProgressEvent`

A single progress update emitted during workflow execution.

```python
@dataclass(frozen=True)
class ProgressEvent:
    session_id: str
    phase: ProgressPhase
    role: AgentRole | None
    step_index: int
    total_steps: int
    substep_label: str
    substep_index: int = 0
    substep_total: int = 1
    granularity: ProgressGranularity = ProgressGranularity.AGENT
    detail: str = ""
    elapsed_ms: float | None = None
    created_at: float = field(default_factory=perf_counter)
```

### `ProgressPhase`

Discrete phases for each workflow step:

- `STEP_STARTED`
- `STEP_SUBSTEP`
- `STEP_COMPLETED`
- `STEP_FAILED`

### `ProgressGranularity`

User-selectable verbosity:

- `AGENT` (1) — coarse, per-agent updates
- `SUBSTEP` (2) — individual substeps like tool calls
- `DETAIL` (3) — fine-grained detail

### `ProgressQueue` and `ProgressReporter`

```python
ProgressQueue = asyncio.Queue[ProgressEvent | None]
ProgressReporter = Callable[[ProgressEvent | None], None]
```

## Session Context

Progress is scoped to a session ID stored in a `contextvars.ContextVar`.

- `current_session_id()` — reads the current context value
- `using_session(session_id)` — context manager that binds a session ID for the block

## The Bus

`Bus` is a class-level registry that holds one `ProgressQueue` and one `asyncio` event loop per session.

```python
Bus.register(session_id, queue)
queue = Bus.get(session_id)
loop = Bus.get_loop(session_id)
Bus.unregister(session_id)
```

This lets emitters fire events from anywhere in the process without passing queues around.

## Emit Functions

All emitters resolve the session ID from the current context if none is provided.

### Core (`progress_emit_core.py`)

- `emit(session_id, phase, role, step_index, total_steps, substep_label, **extra)` — low-level event emission
- `emit_tool_call(role, tool_name, *, args_preview, result_preview, status, session_id)` — ReAct tool call visibility
- `emit_rate_limit(role, *, provider, attempt, max_attempts, delay_sec, reason, session_id)` — retry/back-off events

### Events (`progress_emit_events.py`)

- `emit_handoff(*, direction, role, peer_role, payload_keys, payload_bytes, payload_preview, session_id)` — A2A handoff sent/received
- `emit_claim_verdict(role, claim_id, claim_text, old_verdict, new_verdict, *, confidence, source_count, session_id)` — claim status transitions

### Prompts (`progress_emit_prompts.py`)

- `emit_prompt(role, label, prompt_text, *, system_text, session_id, model)` — prompt sent to an LLM
- `emit_llm_response(role, label, response_text, *, elapsed_ms, prompt_tokens, completion_tokens, finish_reason, model, session_id)` — LLM response received

## Utilities (`progress_utils.py`)

### `create_progress_reporter(loop, queue)`

Builds a thread-safe `ProgressReporter` that uses `loop.call_soon_threadsafe(queue.put_nowait, event)`. Use this when a worker thread needs to push events into an asyncio queue owned by another loop.

### `drain_progress_while_running(queue, workflow_task)`

An async generator that yields `ProgressEvent` items from the queue until the workflow task finishes and the queue is fully drained. It handles sentinel values (`None`) and cancels pending queue gets when the workflow ends.

## Role Step Index

Every emitter uses a fixed role-to-step mapping so the UI can order agents consistently:

| Role | Index |
|------|-------|
| preprocessor | 0 |
| clarifier | 1 |
| planner | 2 |
| searcher | 3 |
| ranker | 4 |
| reader | 5 |
| evidence_deduplicator | 6 |
| fact_checker | 7 |
| adversary | 8 |
| synthesizer | 9 |
| critic | 10 |
| postprocessor | 11 |

## Thread Safety

- `Bus` stores queues and loops in plain class variables; callers should register and unregister from the same loop when possible.
- `emit()` detects whether it is running inside an event loop. If not, it schedules the put on the target loop with `call_soon_threadsafe`.
- `create_progress_reporter` is explicitly designed for cross-thread use.
