# A2A Protocol (`backend.core.a2a`)

This directory implements the Agent-to-Agent (A2A) protocol layer for the research pipeline. It wraps the official `a2a-sdk` with opinionated helpers for card-based discovery, task-based messaging, and HTTP client dispatch. Every module here is grounded in the Google A2A specification and tuned for the multi-agent research system.

## What lives here

| File | Purpose |
|------|---------|
| `__init__.py` | Public package surface. Re-exports `A2AClient`, `AgentRegistry`, message helpers, and `AGENT_CARDS`. |
| `card_specs.py` | Raw specification data mapping each `AgentRole` to name, description, skill, and tags. |
| `cards.py` | Builds `AgentCard` protobuf objects from `card_specs.py` using the compat layer. |
| `client.py` | `A2AClient` — async HTTP client that dispatches `Message` objects to agent services. |
| `client_helpers.py` | Low-level helpers for constructing messages and extracting text or data payloads from `Task` / `Message`. |
| `compat.py` | Compatibility wrappers around `a2a-sdk` constructors (`make_skill`, `make_agent_card`, `build_http_app`). |
| `proto.py` | Protobuf part helpers (`make_text_part`, `make_data_part`, `new_task`, etc.). |
| `registry.py` | `AgentRegistry` — resolves `AgentRole` values to configured HTTP URLs and optional in-process handlers. |
| `request_task.py` | Small helper to resolve the current `Task` inside an `AgentExecutor.execute` callback. |

## Public API

### `get_registry()` → `AgentRegistry`

Lazily constructs and returns the global `AgentRegistry`. The registry is a singleton; subsequent calls return the same instance until `reset_registry()` is called.

### `A2AClient`

Async client for sending tasks to HTTP-backed A2A services.

```python
from a2a_research.backend.core.a2a import A2AClient

client = A2AClient()
result = await client.send(
    role=AgentRole.SEARCHER,
    payload={"query": "climate change impacts 2024"},
    text="",
    task_id="task-123",
    context_id="ctx-456",
    from_role=AgentRole.PLANNER,
)
```

**Constructor**

- `registry` — optional `AgentRegistry` (defaults to `get_registry()`)
- `httpx_client` — optional `httpx.AsyncClient` (created on demand if omitted)

**`send(role, payload=None, *, text="", task_id=None, context_id=None, from_role=None)`**

Builds a `Message`, dispatches it to the agent URL resolved by the registry, and returns the final `Task | Message`. If the registry has an in-process handler registered for the role, the request is handled locally instead of over HTTP.

The method logs every send and response via the application logger, and emits a `handoff` progress event when `session_id` and `from_role` are present.

**`aclose()`**

Closes all cached SDK clients and the underlying `httpx.AsyncClient`.

### `AgentRegistry`

Resolves `AgentRole` values to service URLs and supports in-process execution for tests.

**URL resolution**

The registry reads agent URLs from the global `settings` object:

- `planner_url`
- `searcher_url`
- `reader_url`
- `fact_checker_url`
- `synthesizer_url`
- `clarifier_url`
- `preprocessor_url`
- `ranker_url`
- `evidence_deduplicator_url`
- `adversary_url`
- `critic_url`
- `postprocessor_url`

**In-process handlers**

For unit tests and local execution, you can register an executor factory or an existing `AgentExecutor`:

```python
registry = get_registry()
registry.register_factory(AgentRole.SEARCHER, lambda: my_executor)
```

When a handler exists for a role, `A2AClient.send` routes the request locally through `DefaultRequestHandler` instead of making an HTTP call.

### `build_message(text="", data=None, *, role=ROLE_USER, task_id=None, context_id=None)` → `Message`

Convenience wrapper around `make_message` that builds a protobuf `Message` with text and/or JSON data parts. UUIDs are generated automatically for `message_id`; `task_id` and `context_id` default to empty strings if omitted.

### `extract_data_payloads(task_or_message)` → `list[dict]`

Scans all parts of a `Task` (via its artifacts) or a `Message` and returns every `data` payload found.

### `extract_text(task_or_message)` → `str`

Concatenates all text parts from a `Task` or `Message`, joined by newlines.

### `extract_data_payload_or_warn(task_or_message)` → `dict`

Returns a single data payload, or merges multiple payloads with a warning. Falls back to `{}` when no payload exists.

### `AGENT_CARDS` and `get_card(role)`

`AGENT_CARDS` is a pre-built dictionary mapping every `AgentRole` to an `AgentCard` protobuf. `get_card(role)` looks up the card for a given role. Cards are built from `card_specs.py` and include:

- `name` and `description`
- `url` (from settings)
- A single `AgentSkill` with id, description, and tags
- Streaming enabled, default input/output modes set to `text/plain` and `application/json`

## Protocol helpers (`proto.py`)

These functions work directly with `a2a-sdk` protobuf types:

- `make_text_part(text)` → `Part`
- `make_data_part(data)` → `Part` (serializes Python objects via `google.protobuf.struct_pb2.Value`)
- `get_text_part(part)` → `str | None`
- `get_data_part(part)` → `dict | None`
- `make_message(...)` → `Message` (assembles parts, assigns UUIDs)
- `make_text_message(text, *, role=ROLE_AGENT)` → `Message`
- `new_agent_text_message(text)` → `Message` (convenience alias)
- `new_task(message)` → `Task` (creates a `Task` in `TASK_STATE_SUBMITTED`)

## Compatibility layer (`compat.py`)

Shields the rest of the codebase from `a2a-sdk` constructor churn:

- `make_skill(...)` — builds an `AgentSkill` with safe defaults for tags, examples, and modes.
- `make_agent_card(...)` — builds an `AgentCard` with one `AgentInterface`, capabilities, and skills.
- `build_http_app(agent_card, http_handler)` — assembles a `Starlette` app with the agent-card JSON-RPC routes.

## Card specifications (`card_specs.py`)

`CARD_SPECS` is a plain dictionary keyed by `AgentRole`. Each entry contains:

- `name` — human-readable agent name
- `description` — what the agent does
- `skill_id` and `skill_description` — the primary skill advertised on the card
- `tags` — categorical labels for discovery

Roles covered: `PLANNER`, `SEARCHER`, `READER`, `FACT_CHECKER`, `SYNTHESIZER`, `CLARIFIER`, `PREPROCESSOR`, `RANKER`, `EVIDENCE_DEDUPLICATOR`, `ADVERSARY`, `CRITIC`, `POSTPROCESSOR`.

## Task resolution (`request_task.py`)

`initial_task_or_new(context)` is used inside `AgentExecutor.execute` callbacks. It returns `context.current_task` if one exists; otherwise it creates a fresh `Task` from `context.message`. Raises `ValueError` when both are missing.

## Design notes

- **Streaming support** — `A2AClient` accumulates streaming `StreamResponse` items into a final `Task` or `Message`. The SDK client is created per-role and cached.
- **Local vs remote execution** — The registry's handler seam lets the same `A2AClient` code path run agents in-process (for tests) or over HTTP (for production) without caller changes.
- **Observability** — Every send and response is logged with structured fields (`role`, `url`, `task_state`, `task_id`). Handoff events carry payload previews for the progress UI.
- **Type safety** — All modules use Python 3.11+ type hints and import `a2a-sdk` types under `TYPE_CHECKING` where possible to keep runtime imports minimal.

## Entry point

Most callers should import from the package root:

```python
from a2a_research.backend.core.a2a import A2AClient, get_registry, build_message
```
