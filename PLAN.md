# PLAN.md — a2a_research remediation

Authoritative specification for the coding agent executing the next iteration of this repo. This plan is derived from a full-codebase review conducted on 2026-04-18. Read it end-to-end before making any change.

---

## 0. Summary

Target end state:

- Each of the 5 agents runs as **its own HTTP server process** using the real `a2a-sdk`, with agent cards served at `/.well-known/agent-card.json`.
- The workflow coordinator is a **true A2A client** that discovers and dispatches tasks over HTTP.
- The FactChecker's internal peer calls to Searcher and Reader are **also HTTP** (peer-to-peer A2A), not in-process.
- Every agent emits **real progress events** (`ProgressEvent`) at meaningful substeps, consumed by the Mesop UI in real time.
- Every framework **earns its keep**: PocketFlow branches, smolagents plans with an LLM loop, LangGraph loops, Pydantic AI produces structured output.
- All LLM traffic goes through **OpenRouter only**, using async SDKs (no event-loop blocking).
- Dead code removed, docs aligned with reality, tests updated for the HTTP boundary.

Non-goals:

- Authentication, TLS, push notifications, or multi-user deployment. Localhost HTTP is fine.
- Persisting tasks across process restarts. `InMemoryTaskStore` is fine.
- Multi-node / cross-machine deployment. Single-host only.
- Cross-language interop. Everything stays Python.

---

## 1. Architecture target

```
┌────────────────────────────────────────────────────────────────┐
│ Mesop UI (one process)                                         │
│   └─ drains ProgressQueue, renders timeline                    │
└────────────┬───────────────────────────────────────────────────┘
             │ run_research_async (in-process, UI host)
             ▼
┌────────────────────────────────────────────────────────────────┐
│ Coordinator (same process as UI)                               │
│   HTTP A2A Client ──► Planner       :10001                     │
│   HTTP A2A Client ──► FactChecker   :10004  ◄─ peer A2A ──┐    │
│   HTTP A2A Client ──► Synthesizer   :10005                │    │
└────────────┬───────────────────────────────────────────────┼───┘
             │ (emits ProgressEvent on every substep)        │
             │                                               │
             ▼                                               │
      Planner :10001  (PocketFlow branching flow)            │
                                                             │
      Synthesizer :10005  (Pydantic AI structured output)    │
                                                             │
      FactChecker :10004  (LangGraph loop)                   │
          │   HTTP A2A Client ──► Searcher  :10002 ──────────┤
          │   HTTP A2A Client ──► Reader    :10003 ──────────┘
```

Ports:
- Planner:     `10001`
- Searcher:    `10002`
- Reader:      `10003`
- FactChecker: `10004`
- Synthesizer: `10005`

All configurable via env vars: `PLANNER_URL`, `SEARCHER_URL`, `READER_URL`, `FACT_CHECKER_URL`, `SYNTHESIZER_URL` (defaults to the above on `http://localhost:PORT`).

---

## 2. Operating rules for the coding agent

1. **Work in phases (§4). Every phase ends with a green test run.** Do not start phase N+1 until `make test` passes on phase N. If a phase introduces a feature that breaks existing tests, update the tests in the same phase.
2. **Commit at every phase boundary.** Commit message format: `phase-N: <one-line summary>`. Each commit must pass `make check && make test`.
3. **Do not touch `.env`**. Update `.env.example` and settings only.
4. **Minimize churn.** Do not rewrite clean code just because you're editing nearby. Do not reformat unrelated files.
5. **Keep file sizes reasonable but do not split mechanically** — the old 200-line rule is removed. Split only when a module has two genuinely different responsibilities.
6. **Prefer deletion over deprecation.** When a module is identified as dead, remove it and its imports in the same commit. Do not leave shims.
7. **If a step in this plan is ambiguous, STOP and ask.** Do not invent behaviour. Do not silently swap the architecture.
8. **If you discover a problem this plan didn't anticipate, STOP and surface it.** Document the surprise in your response, then propose a resolution. Do not decide unilaterally.
9. **No new dependencies without explicit approval.** The dependency list in §9 is closed unless you surface a blocker.
10. **Preserve behaviour for callers.** `run_research_async(query: str) -> ResearchSession` and the public API surface in `a2a_research/__init__.py` must remain importable with the same names. Internals can change freely.

---

## 3. Conventions

- Python 3.11+, async-first. Every I/O-bound function is `async def` and uses async SDKs (`AsyncOpenAI`, `AsyncTavilyClient`, `httpx.AsyncClient`).
- Type hints on every function signature. `from __future__ import annotations` at the top of every module.
- Log with `a2a_research.app_logging.get_logger(__name__)` and `log_event(...)` for structured events. Never `print`.
- No `sys.path` hacks, no relative imports beyond one level, no star imports.
- Errors surface. Coercion failures log at WARNING with context. Import failures that are not truly optional re-raise.

---

## 4. Phased implementation plan

Each phase has: **Goal**, **Files**, **Changes**, **Tests**, **Done when**. Complete phases in order.

---

### Phase 1 — Foundation & cleanup (no behaviour change)

**Goal**: get the tree honest before restructuring. Remove dead code, align docs, fix the description, preserve current behaviour.

**Files to delete**:
- `src/a2a_research/models/artifact.py`
- `src/a2a_research/models/policy.py`
- `AGENTS.md` (user is removing this themselves — confirm it's gone before committing)

**Files to edit**:
- `src/a2a_research/models/__init__.py` — remove imports and `__all__` entries for `Artifact`, `ArtifactKind`, `DataArtifact`, `StreamArtifact`, `TextArtifact`, `wrap_in_artifact`, `PolicyEffect`, `WorkflowPolicy`.
- `pyproject.toml` — `description = "5-agent A2A research and verification pipeline (HTTP-orchestrated, OpenRouter-backed)"`. Remove any reference to 4 agents or PocketFlow-as-orchestrator.
- `README.md` — delete the entire **"Example Chat Agent Scaffolds (other frameworks)"** section. Update the architecture diagram to match §1 above (placeholder for now; full rewrite in Phase 8). Update the "5-Agent Web Research & Verification" tagline to say **HTTP-orchestrated**.
- `src/a2a_research/agents/langgraph/__init__.py`, `agents/pydantic_ai/__init__.py`, `agents/smolagents/__init__.py` — confirm empty and leave empty (no change needed unless they have residue).

**Tests**:
- Remove any imports of deleted symbols from `tests/`. None should exist since nothing used them, but grep to confirm: `rg -n 'Artifact|PolicyEffect|WorkflowPolicy|wrap_in_artifact|chat_invoke' src tests`.

**Done when**:
- `make check && make test` passes.
- `rg -n 'chat_invoke|wrap_in_artifact|WorkflowPolicy' .` returns zero matches.
- `README.md` no longer references the chat scaffolds or `chat_invoke`.

---

### Phase 2 — OpenRouter-only async LLM stack

**Goal**: strip `providers.py` to a single OpenRouter-backed async chat model, eliminate event-loop blocking.

**Files**:
- `src/a2a_research/providers.py` — reduce to:
  - One class `OpenRouterChatModel` with `async def ainvoke(self, messages) -> ChatResponse`.
  - Uses `openai.AsyncOpenAI(api_key=settings.llm.api_key, base_url=settings.llm.base_url)`.
  - `get_llm() -> OpenRouterChatModel` returns a cached singleton.
  - `ProviderRequestError`, `ProviderRateLimitError` kept.
  - All Anthropic / Google / Ollama code deleted.
  - `parse_structured_response` kept (still used).
- `src/a2a_research/settings.py` — `LLMSettings`:
  - `provider` field removed. `LLM_PROVIDER` no longer read.
  - `model` default remains `openrouter/elephant-alpha`.
  - `base_url` default remains `https://openrouter.ai/api/v1`.
  - `api_key` required (validate on first use, not at import).
- `pyproject.toml` — remove `anthropic`, `google-genai`, `ollama`. Keep `openai`.
- `.env.example` — drop `LLM_PROVIDER` and all provider-specific sections. Keep only `LLM_MODEL`, `LLM_BASE_URL`, `LLM_API_KEY`. Add a comment: *"All LLM traffic is routed through OpenRouter."*
- `src/a2a_research/agents/pocketflow/planner/nodes.py` — `model.invoke` → `await model.ainvoke`.
- `src/a2a_research/agents/langgraph/fact_checker/verify_route.py` — `model.invoke` → `await model.ainvoke`.
- `src/a2a_research/agents/pydantic_ai/synthesizer/agent.py` — `build_model` simplified: always `OpenAIChatModel(settings.llm.model, provider=OpenAIProvider(base_url=settings.llm.base_url, api_key=settings.llm.api_key))`. Delete Anthropic/Google imports and branches.
- `src/a2a_research/agents/smolagents/searcher/agent.py`, `reader/agent.py` — `OpenAIServerModel(model_id=settings.llm.model, api_base=settings.llm.base_url, api_key=settings.llm.api_key)`. Simplify (no conditional kwargs).

**Tests**:
- `tests/test_providers.py` — replace provider-switching tests with OpenRouter-only tests. Mock `openai.AsyncOpenAI` via `monkeypatch`. Assert that `get_llm().ainvoke(...)` works with a fake async client.
- `tests/test_agent_planner.py`, `test_agent_fact_checker.py`, `test_workflow_integration.py` — adjust `_fake_llm` / `_llm_stub` to expose `ainvoke` as an async method, not `invoke`. Example: `model.ainvoke = AsyncMock(return_value=MagicMock(content=json.dumps(payload)))`.
- `tests/test_settings.py` — remove provider-enum tests; confirm only OpenRouter keys are validated.

**Done when**:
- `rg -n 'Anthropic|GoogleProvider|OllamaProvider|genai|\.ainvoke|\.invoke\(' src/a2a_research/providers.py src/a2a_research/agents/ | grep -v ainvoke` returns zero hits for sync invoke in async contexts.
- `make test` passes.
- `python -c "from a2a_research.providers import get_llm; import asyncio; asyncio.run(get_llm().ainvoke([{'role':'user','content':'ping'}]))"` exercises the real HTTP path end-to-end (requires API key; smoke test, not in CI).

---

### Phase 3 — Progress events wired end-to-end

**Goal**: replace the UI's fake progress bar with real, substep-level events emitted by every agent.

**Design**:
- `progress.py` stays (it's already well-designed). One addition: a new helper `async def emit(reporter, phase, role, step_index, total_steps, substep_label, **extra)` that constructs a `ProgressEvent` and calls the reporter. This reduces boilerplate at every emit site.
- **Every executor's `execute()` method accepts a reporter** via `RequestContext.metadata` (A2A has no first-class field for this, but we can pass a correlation ID and use a module-level in-process queue keyed by that ID — see below).

**Concrete mechanism**:
- The coordinator creates a `ProgressQueue` per session, registers it in an `a2a_research.progress.Bus` keyed by `session_id`.
- Each outbound A2A message includes `session_id` in its `DataPart` payload (already the case for most payloads; standardize it).
- Each executor pulls `session_id` out of the payload and emits events to `Bus.get(session_id)` if present. If absent, emissions are silently dropped (tests and standalone demo don't care).
- The UI's submit handler drains the queue while `run_research_async` runs, applying each event to `AppState` for rendering.

**Files**:
- `src/a2a_research/progress.py`:
  - Add `Bus` class: `Bus.register(session_id, queue)`, `Bus.get(session_id) -> ProgressQueue | None`, `Bus.unregister(session_id)`.
  - Add `emit(session_id, phase, role, step_index, total_steps, substep_label, **extra)` helper that looks up the queue and puts the event.
  - Tweak `ProgressEvent` to carry `session_id: str` (new required field).
- `src/a2a_research/workflow/coordinator.py`:
  - Accept an optional `progress_queue: ProgressQueue | None` parameter on `run_research_async`.
  - If present, register it in `Bus` under `session.id` for the duration of the run, unregister in `finally`.
  - Include `session_id` in every payload sent to Planner / FactChecker / Synthesizer.
  - Emit top-level `STEP_STARTED` / `STEP_COMPLETED` / `STEP_FAILED` events around each agent call.
- Each executor (`planner/main.py`, `searcher/main.py`, `reader/main.py`, `fact_checker/main.py`, `synthesizer/main.py`):
  - Read `session_id` out of the incoming `DataPart`.
  - Emit `STEP_SUBSTEP` events at meaningful checkpoints (see table below).
- **FactChecker specifically** (most important): emit events inside each LangGraph node so the UI sees search rounds, read rounds, verify rounds individually.

**Substep checkpoints** (minimum required — add more if natural):

| Agent | Substeps to emit |
|---|---|
| Planner | `classify`, `decompose`, `seed_queries` (after Phase 4) |
| Searcher | per-query: `search_query_<n>` with result count and provider status |
| Reader | per-url: `fetch_url_<n>` with title or error |
| FactChecker | `round_<n>_search`, `round_<n>_read`, `round_<n>_verify`, `converged` / `exhausted` |
| Synthesizer | `building_prompt`, `llm_call`, `rendering_markdown` |

- `src/a2a_research/ui/app.py`:
  - Replace the `asyncio.sleep(0.5)` fake loop with real drain-while-running using `drain_progress_while_running`.
  - Map each `ProgressEvent` to UI state: set `current_substep`, update `progress_pct` based on `(step_index + substep_index/substep_total) / total_steps`, append to `progress_running_substeps` on START, remove on COMPLETED.
  - The granularity selector now actually filters: AGENT (step events only), SUBSTEP (step + substep), DETAIL (everything including `detail` fields).

**Tests**:
- `tests/test_progress.py` — new tests:
  - `Bus.register` / `get` / `unregister` lifecycle.
  - `emit` returns silently when no queue registered.
  - `drain_progress_while_running` yields all events and stops on workflow completion.
- `tests/test_workflow_integration.py` — add `test_progress_events_emitted`: runs the pipeline with a queue, asserts receipt of at least one `STEP_STARTED` per role plus FactChecker round events.

**Done when**:
- Running the UI against live (or mocked) pipeline shows per-agent substep status, not a fake % bar.
- The granularity selector visibly changes the level of detail.
- Tests cover the queue lifecycle and event emission per role.

---

### Phase 4 — Frameworks earn their keep (still in-process)

**Goal**: make PocketFlow, smolagents, and Pydantic AI each do something non-trivial. Do this before HTTP splitting so we can iterate quickly.

#### 4a. Planner (PocketFlow) — branching flow

Replace the single-node `DecomposeNode` with a genuine multi-node flow:

```
ClassifyNode ──► DecomposeFactualNode    ──► SeedQueryNode ──► TerminalNode
         │                                                   ▲
         ├──► DecomposeComparativeNode   ──► SeedQueryNode ──┤
         │                                                   │
         └──► DecomposeTemporalNode      ──► SeedQueryNode ──┘

         (any path fails) ──► FallbackNode
```

- `ClassifyNode`: LLM classifies the query as `factual | comparative | temporal | other`. Outputs one of those action keys.
- `DecomposeFactualNode`, `DecomposeComparativeNode`, `DecomposeTemporalNode`: each has a distinct system prompt optimized for its query type. Output `claims`.
- `SeedQueryNode`: given claims + classification, generates tuned seed queries.
- `FallbackNode`: unchanged — single claim equal to raw query.

This uses PocketFlow's branching (`node - "action" >> next`) meaningfully.

**Files**: `src/a2a_research/agents/pocketflow/planner/nodes.py`, `flow.py`, `prompt.py` (split into `prompts.py` with per-node prompts).

#### 4b. Searcher (smolagents) — agentic query refinement

The SearcherExecutor currently bypasses smolagents. Rewire it to use a `ToolCallingAgent` that:

- Takes the initial query list as input.
- Has `web_search(query: str) -> list[hit]` as a tool.
- Reasons with the LLM across up to `max_steps=5` turns: runs initial searches, inspects results, and issues refined queries if results are weak (empty, low-score, or off-topic).
- Emits progress events between tool calls.

**Files**: `src/a2a_research/agents/smolagents/searcher/main.py`, `agent.py`, `tools.py`, `prompt.py`.

Key change: `SearcherExecutor.execute` now calls `build_agent().run(prompt)` instead of `search_queries()` directly. `search_queries` (the old parallel helper) stays as a utility the agent's tool can invoke for parallel fan-out on one turn.

#### 4c. Reader (smolagents) — agentic page selection

Same pattern: rewire ReaderExecutor to use a `ToolCallingAgent` that:

- Takes a URL list + a "what are we trying to verify" hint (pass the FactChecker's current claims in the payload).
- Has `fetch_and_extract(url)` as a tool.
- Fetches pages in order of relevance estimate, stops early if it has enough high-quality evidence, skips obvious junk domains.
- Emits progress events per fetch.

**Files**: `src/a2a_research/agents/smolagents/reader/main.py`, `agent.py`, `tools.py`, `prompt.py`.

The FactChecker's `ask_reader_node` must now pass the current claims in its payload so the Reader agent has context for prioritization.

#### 4d. Synthesizer (Pydantic AI) — already earning its keep, light polish only

No architectural change. Small improvements:
- Add instructions to `SYNTHESIZER_PROMPT` encouraging section-level structure based on claims.
- Verify that `ReportOutput` is actually being produced (not just the fallback) in the happy-path integration test.

**Tests**:
- `tests/test_agent_planner.py` — add tests for each classification branch (factual / comparative / temporal / other).
- `tests/test_agent_searcher.py` — add `test_searcher_refines_weak_queries`: first `web_search` call returns no hits, agent reformulates and calls again.
- `tests/test_agent_reader.py` — add `test_reader_stops_early_when_enough_evidence`.
- `tests/test_workflow_integration.py` — update `test_full_pipeline` to mock the smolagents `ToolCallingAgent.run` path instead of the direct tool path.

**Done when**:
- Each of the three frameworks has at least one test asserting behaviour that would not work without that framework's core feature (branching / tool-calling loop / structured output).
- `make test` passes.

---

### Phase 5 — Split to real A2A over HTTP

**Goal**: each agent runs as an independent `a2a-sdk` HTTP server. The coordinator and FactChecker talk to peers over HTTP.

**Reference**: https://a2a-protocol.org/latest/tutorials/python/ and the `a2a-samples` repo's `samples/python/agents/langgraph/` example.

#### 5a. Server infrastructure per agent

Add to each of `agents/{pocketflow/planner, smolagents/searcher, smolagents/reader, langgraph/fact_checker, pydantic_ai/synthesizer}/`:

- `__main__.py` — CLI entrypoint using `uvicorn.run`:
  ```python
  # pattern (adapt per agent)
  import uvicorn
  from a2a.server.apps import A2AStarletteApplication
  from a2a.server.request_handlers import DefaultRequestHandler
  from a2a.server.tasks import InMemoryTaskStore
  from a2a_research.agents.<X>.main import <X>Executor
  from a2a_research.agents.<X>.card import <X>_CARD
  from a2a_research.settings import settings

  def main() -> None:
      handler = DefaultRequestHandler(
          agent_executor=<X>Executor(),
          task_store=InMemoryTaskStore(),
      )
      server = A2AStarletteApplication(agent_card=<X>_CARD, http_handler=handler)
      uvicorn.run(server.build(), host="0.0.0.0", port=settings.<x>_port)

  if __name__ == "__main__":
      main()
  ```
- `card.py` — update the AgentCard URL to `http://localhost:<PORT>` (read from settings), `preferred_transport="JSONRPC"`, `capabilities=AgentCapabilities(streaming=True)` (streaming is genuinely useful now).

#### 5b. Settings additions

`src/a2a_research/settings.py`:
```python
planner_port: int = 10001
searcher_port: int = 10002
reader_port: int = 10003
fact_checker_port: int = 10004
synthesizer_port: int = 10005

planner_url: str = "http://localhost:10001"
searcher_url: str = "http://localhost:10002"
reader_url: str = "http://localhost:10003"
fact_checker_url: str = "http://localhost:10004"
synthesizer_url: str = "http://localhost:10005"
```

Matching `.env.example` entries.

#### 5c. Rewrite `a2a_research/a2a/` — HTTP client

- `client.py` — `A2AClient` becomes an HTTP wrapper around `a2a.client.Client`:
  - Holds a shared `httpx.AsyncClient` (lazy).
  - `send(role, payload, ...)` — looks up URL for role, resolves agent card on first use, calls `send_message` or `send_message_streaming` via the sdk's client.
  - Returns the final `Task` or a `Message`.
  - Streaming path consumes SSE and forwards `TaskStatusUpdateEvent` and `TaskArtifactUpdateEvent` events to the caller (for FactChecker use).
- `registry.py` — becomes URL resolution, not executor registration:
  - `AgentRegistry.get_url(role) -> str`.
  - No more in-process executor instantiation.
- `cards.py` — `get_card(role) -> AgentCard` still serves the static cards for the servers to advertise. The client fetches live cards over HTTP.

#### 5d. Coordinator uses HTTP client

`workflow/coordinator.py`: no structural change in flow, but `A2AClient(get_registry())` now returns an HTTP client. Error surface is richer — capture `httpx.ConnectError` as "agent not reachable" with the URL in the message.

#### 5e. FactChecker uses HTTP client for peer agents

`agents/langgraph/fact_checker/main.py` — `run_fact_check` accepts an HTTP `A2AClient` (defaults to one pointing at the configured Searcher/Reader URLs).

`search_reader_nodes.py` — `client.send(AgentRole.SEARCHER, payload={...})` now hits `http://localhost:10002` (or configured URL).

#### 5f. Launcher

New file: `src/a2a_research/launcher.py` — starts all 5 servers as subprocesses, streams their logs to stdout with prefixes, handles SIGINT cleanly.

New Makefile targets:
- `make serve-all` — runs the launcher.
- `make serve-<name>` — runs one agent (e.g. `make serve-planner`).

#### 5g. UI integration

Two options — pick **Option A** unless you discover a blocker:

**Option A (default)**: UI process imports and calls `run_research_async` (HTTP client inside). User runs `make serve-all` in one terminal and `make mesop` in another. Document this in README.

**Option B**: UI's `_on_submit` spawns the agent subprocesses itself via the launcher. More magic, more failure modes. Skip unless Option A proves painful.

**Tests**:

This is the hardest testing change. Strategy:

- Keep **executor-level unit tests** (phase 1–4 tests) unchanged — they instantiate executors directly and drive them with a fake `RequestContext`. These don't need HTTP.
- Add **HTTP contract tests** per agent in `tests/test_agent_<name>_http.py`:
  - Spin up the agent's `A2AStarletteApplication` in-process via `httpx.ASGITransport` (no real port, no uvicorn).
  - Send real A2A messages through the sdk's client.
  - Assert artifact shape.
- Update `test_workflow_integration.py` to use the ASGITransport pattern to stand up all 5 agents in-process for the full pipeline test. No subprocess orchestration needed.
- Keep `test_a2a_client.py` but rewrite it as an HTTP test using ASGITransport.

Use `httpx.AsyncClient(transport=httpx.ASGITransport(app=server.build()))` to route HTTP requests through the sdk app without binding a port. This is standard httpx testing practice.

**Done when**:
- `make serve-all` starts all 5 services and each responds on `GET /.well-known/agent-card.json`.
- `make mesop` (in another shell) runs queries end-to-end via HTTP.
- `make test` passes with the new HTTP contract tests.
- Killing one agent process produces a clean "agent not reachable" error in the coordinator (not a crash).

---

### Phase 6 — Correctness hardening

**Goal**: fix the remaining bugs and nits surfaced in the review.

#### 6a. Don't silently swallow import failures

`a2a/registry.py` no longer exists in its old form after Phase 5. Apply the principle to any residual "try-import and skip" code: log at WARNING with the full exception, re-raise `AttributeError` (it indicates a code bug, not a missing optional dep).

#### 6b. Log on coercion failure

`workflow/coordinator.py` — `_coerce_claim`, `_coerce_source`, `_coerce_report`: on `ValidationError`, `logger.warning("Failed to coerce %s from payload: %s", <kind>, exc)` and return `None` as before.

Similarly `agents/langgraph/fact_checker/node_support.py` — `parse_verifier` logs at WARNING when the fallback path is taken, with the offending raw content truncated to 200 chars.

#### 6c. `extract_data_payloads` doesn't drop payloads

`a2a/client.py` — add a new helper `extract_data_payload_or_warn(task) -> dict` that:
- Returns the single payload if exactly one.
- Logs WARNING and concatenates dicts (later keys win) if multiple.
- Returns `{}` if none.

Update `workflow/coordinator.py._payload` to use it. Update FactChecker nodes similarly.

#### 6d. SearchResult as a Pydantic model (already is) — drop the 3-tuple

`agents/smolagents/searcher/main.py` — `search_queries` currently returns `tuple[list[WebHit], list[str], list[str]]`. Replace with a small Pydantic model `SearcherBatchResult` (fields: `hits`, `errors`, `providers_successful`) and return that. Update all call sites.

#### 6e. Use `TaskStatus.message` for failures

Every executor currently does `metadata={"error": error_text}` on `TaskStatusUpdateEvent`. Per A2A spec, failure reasons belong in `TaskStatus.message`. Change to:
```python
TaskStatus(
    state=TaskState.failed,
    message=new_agent_text_message(error_text) if error_text else None,
)
```
(Use `a2a.utils.new_agent_text_message`.)

Update `node_support.task_error_metadata` to read from `status.message` instead of `status.metadata`.

#### 6f. Migrate `duckduckgo-search` to `ddgs`

`pyproject.toml` — replace `duckduckgo-search>=7.0.0` with `ddgs>=9.0.0` (or latest).
`tools/search.py` — change `from duckduckgo_search import DDGS` to `from ddgs import DDGS`. Verify the API surface is identical for the calls used (`DDGS().text(query, max_results=...)`).

#### 6g. Cache LangGraph compilation per-process

`agents/langgraph/fact_checker/graph.py` — module-level `_COMPILED_GRAPH: CompiledGraph | None = None`. `build_fact_check_graph(client)` lazily compiles the graph once (the `client` is passed to nodes via a closure at node-build time, but the graph structure is static — restructure so compilation is client-agnostic and client is passed via state instead, OR keep one-graph-per-client in a dict keyed by `id(client)`).

Cleanest: pass the client through state rather than closure. State gets an extra key `_client` that nodes read. Then compile once at import time.

**Tests**:
- `test_a2a_client.py` — expand: multi-payload handling, warn behaviour.
- `test_agent_searcher.py` — assert the returned type is `SearcherBatchResult`.
- `test_agent_<role>.py` for each — assert failed tasks carry a message, not metadata.
- `test_tools_search.py` — update import path to `ddgs`.

**Done when**:
- `make check && make test` passes.
- `rg 'duckduckgo_search' .` returns zero matches.
- `rg 'metadata=\{"error"' .` returns zero matches.

---

### Phase 7 — Documentation

**Goal**: docs reflect reality.

- `README.md` — rewrite the Architecture and Quick Start sections to match the HTTP-split design. Sections needed: Overview, Architecture diagram (ASCII), Quick Start (env setup, `make serve-all`, `make mesop`), Configuration (env vars incl. new `*_URL` / `*_PORT`), Testing, Troubleshooting (what to do when an agent fails to start, how to run one agent alone).
- `docs/` — split into:
  - `docs/architecture.md` — the full system picture, why each framework was chosen, the A2A message flow.
  - `docs/development.md` — running locally, testing, adding an agent, debugging.
  - `docs/progress-events.md` — how the progress bus works, how to add a new event.
- `.env.example` — annotated example with every variable documented.

---

### Phase 8 — Final verification

Run in order:

1. `make clean && make install`
2. `make check` (lint, typecheck, format)
3. `make test` (full suite + coverage)
4. `make serve-all` (in terminal A)
5. `make mesop` (in terminal B)
6. Submit the README's demo query ("What is retrieval-augmented generation?") — verify: all 5 agents show activity in the timeline with per-substep detail, final report renders, sources panel populated.
7. Kill one agent mid-query — verify the coordinator reports which agent is unreachable and the error banner surfaces it.
8. Restart with no `TAVILY_API_KEY` — verify graceful degradation to DDG-only search (existing behaviour must be preserved).

All eight steps must pass before declaring the plan complete.

---

## 5. Test strategy summary

| Layer | Strategy | Files |
|---|---|---|
| Unit — executors | Direct executor instantiation, `RequestContext` built manually, mocked LLM/tool dependencies. | `tests/test_agent_*.py` |
| Unit — tools | Existing pattern unchanged. | `tests/test_tools_*.py` |
| Contract — HTTP | `httpx.ASGITransport` against each `A2AStarletteApplication`, drive via `a2a.client.Client`. | `tests/test_agent_*_http.py` (new) |
| Integration | All 5 agents stood up via ASGITransport, coordinator runs end-to-end in one process. | `tests/test_workflow_integration.py` |
| Progress events | Queue registered, drain while workflow runs, assert event sequence. | `tests/test_progress.py` |
| UI | Mesop component rendering tests, unchanged. | `tests/test_ui_*.py` |

No real network calls in tests. No real ports bound in tests.

---

## 6. Out of scope (do not do)

- Authentication, signed agent cards, or access control. Agents trust each other.
- Redis / Postgres task store.
- Docker Compose setup.
- Multiple model providers. OpenRouter only.
- Replacing Mesop with a different UI framework.
- Adding new agent roles.
- Publishing to PyPI.

---

## 7. Rollback

Every phase ends with a passing commit. If a later phase introduces an unrecoverable issue, `git reset --hard <last-good-commit>` and replan from that point with the user.

---

## 8. Commit log (the agent fills this in)

- [x] Phase 1 — `02f283f81428d2ae219653c186648ed222080654` — foundation & cleanup
- [x] Phase 2 — `390eb8009ba0c6ae3ba80eb59c8930ba5cc121fa` — OpenRouter-only async LLM
- [x] Phase 3 — `17c80420cb0bd51a59753513078b1fcfe2f603e5` — progress events wired
- [x] Phase 4 — `c6cec371a3afdb70b7fd09fc91fb90781adb9038` — frameworks earn their keep
- [x] Phase 5 — `c2d98e921d44e8c179766d5183d975dded4651ea` — HTTP split with real a2a-sdk
- [x] Phase 6 — `f8d35e8f7752e63620314387abd2a86a75270207` — correctness hardening & nits
- [x] Phase 7 — `2417354efc0d4d6d57a198090dd70231d59eea0a` — documentation
- [x] Phase 8 — `0eb40a8c7fe2fed1f0de6b1149c9532ec72f1cc8` — final verification

---

## 9. Dependency diff

Removed: `anthropic`, `google-genai`, `ollama`, `duckduckgo-search`.
Added: `ddgs>=9.0.0`, `uvicorn[standard]>=0.30` (if not already transitively present via a2a-sdk), `httpx>=0.27` (likewise).
Unchanged: everything else.
