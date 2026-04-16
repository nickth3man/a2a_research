# PROJECT KNOWLEDGE BASE

**Generated:** 2026-04-16
**Commit:** dbde119
**Branch:** dev

## OVERVIEW
Local-first 4-agent research system. PocketFlow orchestrates Researcher → Analyst → Verifier → Presenter over an in-process A2A layer, Chroma-backed RAG corpus, and a Mesop UI.

## STRUCTURE
```text
./
├── src/a2a_research/          # package root
│   ├── workflow/              # PocketFlow runtime; stable public entrypoint lives here
│   ├── ui/                    # Mesop app + component system
│   ├── a2a/                   # in-process client/server facade over registered handlers
│   ├── agents/                # all four invoke functions live in one large __init__.py
│   ├── rag/                   # Chroma ingestion/retrieval
│   ├── models/                # shared Pydantic domain types
│   ├── prompts/               # system prompt strings
│   └── helpers/               # deterministic report formatting helpers + PocketFlow nodes
├── tests/                     # flat pytest suite; strong UI/workflow coverage
├── data/corpus/               # markdown corpus to ingest
├── data/chroma/               # local Chroma persistence; generated, gitignored
└── logs/                      # first stop for runtime failures; includes text logs + screenshots
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Run pipeline from code | `src/a2a_research/workflow/__init__.py` | `run_research_sync` is the stable blocking entrypoint |
| Understand orchestration | `src/a2a_research/workflow/AGENTS.md` | entrypoint matrix, shared state contract, event-loop traps |
| Change UI behavior | `src/a2a_research/ui/AGENTS.md` | Mesop state, component boundaries, test stubs |
| Add/change agent logic | `src/a2a_research/agents/__init__.py` | monolithic hotspot; all four invoke functions live here |
| Register a new agent role | `a2a/__init__.py`, `models/__init__.py`, `prompts/__init__.py`, `workflow/builder.py` | must touch all four |
| Provider or model wiring | `src/a2a_research/providers.py` | only place to add LLM/embedding backends |
| RAG ingestion/retrieval | `src/a2a_research/rag/__init__.py` | idempotent ingest; auto-recovers from embedding dimension mismatch |
| Shared data contracts | `src/a2a_research/models/__init__.py` | `ResearchSession`, `Claim`, `AgentResult`, `AgentRole` |
| Debug runtime failures | `logs/` | read this before source-diving |
| Write or extend tests | `tests/AGENTS.md` | singleton reset fixture + Mesop stubs |

## CODE MAP
| Symbol | Type | Location | Role |
|---|---|---|---|
| `run_research_sync` | function | `workflow/__init__.py` | canonical blocking API |
| `get_workflow` | function | `workflow/builder.py` | builds flow + shared dict |
| `ActorNode` | class | `workflow/nodes.py` | wraps agent execution through A2A |
| `run_workflow` / `run_workflow_async` | functions | `workflow/entrypoints.py` | main async orchestration |
| `main_page` | function | `ui/app.py` | only Mesop page |
| `AppState` | state class | `ui/app.py` | Mesop-serializable UI state |
| `researcher_invoke` | function | `agents/__init__.py` | retrieval + summary stage |
| `verifier_invoke` | function | `agents/__init__.py` | verdict assignment |
| `ResearchSession` | model | `models/__init__.py` | shared session source of truth |
| `get_llm` / `get_embedder` | functions | `providers.py` | provider abstraction chokepoint |
| `ingest_corpus` / `retrieve_chunks` | functions | `rag/__init__.py` | corpus build + retrieval |

## CONVENTIONS
- Use `uv` for everything. Repo is managed by `pyproject.toml` + `uv.lock`.
- Verification sequence: `make check` then `make test`.
- `make check` means Ruff lint + Ruff format check + mypy + ty. CI runs the same four checks plus tests.
- mypy is strict, but `ui.*`, `workflow.*`, and `helpers` are intentionally relaxed. `pocketflow.*` is ignored.
- Unit tests require no API key. LLM calls are mocked.
- `run_research_sync` is the public workflow import path; do not add new callers to older coordinator surfaces unless needed.

## ANTI-PATTERNS (THIS PROJECT)
- Do not add a new agent in only one place; role registration spans four files.
- Do not call sync workflow helpers from inside an active event loop; use async entrypoints there.
- Do not make `AppState.session` optional/union-typed; Mesop skips optional Pydantic fields and breaks round-trips.
- Do not scatter provider SDK usage outside `providers.py`.
- Do not bypass `tests/conftest.py` singleton resets when adding new cached globals; extend that fixture instead.
- Do not ignore `/logs`; runtime evidence is usually faster than source spelunking.

## UNIQUE STYLES
- `agents/__init__.py` is intentionally monolithic: all four agent implementations, fallback parsers, and progress emitters are colocated.
- `helpers/__init__.py` is not just string helpers; it also contains PocketFlow report nodes.
- `ui/` is architected like a small design system: tokens, primitives, state helpers, and a component package.
- `logs/` mixes plain-text runtime logs with screenshot artifacts from UI debugging.

## COMMANDS
```bash
make dev
make check
make test
make mesop
make ingest

uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run ty check src/
uv run pytest
```

## NOTES
- Mesop dev server sets `MESOP_STATE_SESSION_BACKEND=memory` to avoid hot-reload state desync.
- Default UI port is `http://localhost:32123`.
- `.env` is loaded automatically through `pydantic-settings`; unknown non-`MESOP_*` keys raise at import time.
- Child docs with local detail: `src/a2a_research/ui/AGENTS.md`, `src/a2a_research/workflow/AGENTS.md`, `tests/AGENTS.md`.
