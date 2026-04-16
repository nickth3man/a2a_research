# POCKETFLOW AGENTS KNOWLEDGE BASE

## OVERVIEW
PocketFlow runtime for the research pipeline. This package owns per-agent handlers (Researcher → Analyst → Verifier → Presenter), the shared agent registry, the composed `AsyncFlow`, sync/async entrypoints, and shared utilities. The A2A protocol surface lives in a sibling package (`a2a_research.a2a`); this package registers handlers for the in-process A2A dispatch layer.

Each named agent folder contains the canonical 4-file PocketFlow-style layout (`main.py` / `flow.py` / `nodes.py` / `utils.py`) so it can be reasoned about — and, for `flow.py`, invoked — standalone. The top-level `flow.py` composes the four agent nodes into the full pipeline.

## STRUCTURE
```text
agents/pocketflow/
├── __init__.py            # Public re-exports; importing this package triggers agent registration
├── flow.py                # build_workflow / get_workflow — composed pipeline over all roles
├── entrypoints.py         # run_workflow / run_workflow_async / run_workflow_sync + timeout handling
├── researcher/
│   ├── __init__.py        # register_agent(...) on import
│   ├── prompt.py          # researcher system prompt
│   ├── main.py            # researcher_invoke(session, message) — RAG + LLM summary
│   ├── nodes.py           # create_node() — ActorNode factory bound to RESEARCHER
│   ├── flow.py            # build_flow() — single-node AsyncFlow for standalone use
│   └── utils.py           # SENDER + build_payload(session) for A2A dispatch
├── analyst/               # same shape — analyst_invoke + claim extraction
├── verifier/
│   ├── __init__.py
│   ├── prompt.py
│   ├── main.py            # verifier_invoke — RAG-grounded verdict assignment
│   ├── nodes.py
│   ├── flow.py
│   └── utils.py           # SENDER + build_payload + parse_verified_claims (JSON + line-mode fallback)
├── presenter/             # same shape — presenter_invoke (markdown report synthesis)
└── utils/                 # Shared utilities; single patch-point for tests
    ├── __init__.py        # convenience re-exports
    ├── registry.py        # AgentSpec, AgentRegistry, register_agent decorator
    ├── nodes.py           # generic ActorNode base + create_actor_node factory
    ├── actor_helpers.py   # role → agent-utils dispatcher (build_payload, get_sender_for_role)
    ├── policy.py          # PipelineOrderPolicy
    ├── adapter.py         # SyncWorkflowAdapter.invoke() / ainvoke()
    ├── coordinator.py     # legacy linear 4-role AsyncFlow builder
    ├── llm.py             # call_llm — thin Provider.call wrapper
    ├── sanitize.py        # sanitize_query — whitespace collapse + 10k truncate
    ├── progress.py        # extract_progress_context, create_substep_emitter
    ├── fallbacks.py       # fallback_research_summary, fallback_verified_claims
    ├── results.py         # create_agent_result factory
    ├── shared_store.py    # build_shared_store — PocketFlow Shared Store schema
    └── helpers.py         # parse_json_safely, build_markdown_report, extract_claims_from_llm_output, formatting helpers
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Stable public imports | `__init__.py` | `run_research_sync`, `run_workflow_async`, `get_graph`, `create_pocketflow_workflow`, all `<role>_invoke` handlers |
| Register a new agent role | `<role>/__init__.py` | Call `register_agent(AgentRole.X, ...)` on the handler in `main.py` |
| Change an agent's system prompt | `<role>/prompt.py` | One module string constant per role |
| Change an agent's logic | `<role>/main.py` | Uses `utils.llm`, `utils.sanitize`, `utils.progress`, `utils.fallbacks`, `utils.results` |
| Change an agent's A2A payload shape | `<role>/utils.py::build_payload` | Role-owned; `utils/actor_helpers.py` dispatches here |
| Change upstream sender mapping for a role | `<role>/utils.py::SENDER` | Role-owned; `utils/actor_helpers.get_sender_for_role` dispatches here |
| Assemble flow from roles | `flow.py` | `build_workflow`, `get_workflow` |
| Patch LLM in tests | `a2a_research.agents.pocketflow.utils.llm.call_llm` | Single mock point; all agents import the `llm` module, not the function |
| Patch RAG retrieval in tests | `a2a_research.rag.retrieve_chunks` | Agents call `rag.retrieve_chunks(...)`; patch at the definition site |
| Parse LLM claim output | `verifier/utils.py`, `utils/helpers.py` | `parse_verified_claims`, `parse_claims_from_analyst`, `extract_claims_from_llm_output` |
| Build the markdown report | `utils/helpers.py::build_markdown_report` | Deterministic fallback the presenter uses when the LLM returns empty |
| Shared state schema | `utils/shared_store.py::build_shared_store` | Canonical keys the ActorNode/Flow depend on |
| Run workflow async | `entrypoints.py` | Primary runtime path; timeout behavior is contractual |
| Use sync adapter object | `utils/adapter.py` | `invoke` wraps `asyncio.run`; do not call from inside a running loop |

## CONVENTIONS
- Each agent folder carries the 4-file PocketFlow layout: `main.py` (handler), `flow.py` (standalone single-node `AsyncFlow`), `nodes.py` (ActorNode factory for that role), `utils.py` (role-owned `SENDER` + `build_payload`, plus role-specific parsers where needed). `__init__.py` and `prompt.py` sit alongside them.
- Handlers are registered on module import via `register_agent(...)`. Importing `a2a_research.agents.pocketflow` imports each subpackage and therefore populates the registry.
- Agents must import utility *modules* (e.g. `from ..utils import llm as llm_utils; llm_utils.call_llm(...)`), not individual functions. This keeps mocks singular: `patch("a2a_research.agents.pocketflow.utils.llm.call_llm")` applies to every agent.
- RAG is imported the same way: `from a2a_research import rag; rag.retrieve_chunks(...)`. Test patching targets `a2a_research.rag.retrieve_chunks`.
- Shared workflow state must include `session`; progress support is threaded through `progress_reporter` via `utils.progress`.
- `flow.py` rejects empty role lists; role ordering is explicit, not inferred.
- Timeout behavior is part of the contract: long-running flows return a partial session with running agents marked failed.
- Role-specific A2A payload shape lives in the agent's own `utils.py`; the generic `ActorNode` in `utils/nodes.py` stays role-agnostic and dispatches through `utils/actor_helpers.py`.

## ANTI-PATTERNS
- Do not put agent code directly in `agents/__init__.py`. That file is a thin re-export layer that delegates to `agents.pocketflow`.
- Do not reach across agent folders. If two agents need the same helper, move it to `utils/`.
- Do not import functions directly into agent modules (`from ..utils.llm import call_llm`). Import the module so a single `patch` can cover every call site.
- Do not call `run_workflow_sync` or `SyncWorkflowAdapter.invoke()` from inside an existing event loop.
- Do not bypass `ActorNode` and call handlers directly if you still expect A2A/progress/session semantics.
- Do not put arbitrary (non-JSON-serializable) objects into message payloads; the progress reporter is attached as a private attribute specifically because payloads are serialized.
- Do not add a role to the flow without the full registration contract: folder + `prompt.py` + `main.py` + `nodes.py` (ActorNode factory) + `flow.py` (single-node AsyncFlow) + `utils.py` (`SENDER` + `build_payload`) + `register_agent(...)` in `__init__.py`, plus an `AgentRole` enum value.
- Do not add role-specific branches to `utils/actor_helpers.py`. It is a pure dispatcher — put the branch's logic in the agent's own `utils.py`.

## EDGE NOTES
- `utils/coordinator.py` is a compatibility surface; the generic `flow.py` + `entrypoints.py` path is the main architecture.
- `utils/helpers.py` hosts deterministic presenter fallbacks (`build_markdown_report`, `format_claims_section`); reporting logic is intentionally co-located with formatting helpers so the Presenter agent can degrade gracefully when the LLM is rate-limited or returns empty content.
- The A2A server (`a2a_research.a2a.server`) looks up handlers by role via lazy imports of `agents.pocketflow.<role>` (which re-exports `<role>_invoke` from `main.py`); changing a handler's module path requires updating `_build_server_registry`.
- Each agent's `flow.py::build_flow()` returns a single-node `AsyncFlow` bound to that agent — intended for unit-testing or local probing of a single role. The composed pipeline is built by the top-level `flow.py::build_workflow()`.
- `utils/actor_helpers.py` uses lazy imports so it never participates in the package bootstrap cycle (each agent's `__init__.py` is imported first to register handlers; the dispatcher is called only at message-send time).
