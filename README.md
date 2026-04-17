# A2A Research — 5-Agent Web Research & Verification

**A research-and-verification pipeline** coordinated by an in-process [A2A](https://github.com/a2aproject/A2A/) registry and client. Five agents — Planner, Searcher, Reader, FactChecker, Synthesizer — run on a mix of runtimes (PocketFlow planner, smolagents search/read, LangGraph fact-check loop, Pydantic AI synthesis). The system uses live web search and page extraction instead of a local RAG corpus: it decomposes queries into claims, gathers evidence from the public web, verifies claims, and renders a structured markdown report.

---

## Architecture

```
                    ┌── Searcher (web search)
Planner ──► FactChecker ──┤── Reader (fetch + extract) ──► … loop … ──► Synthesizer
                    └──────────────────────────────────────────────────┘
```

| Agent | Runtime | Role | Output |
|---|---|---|---|
| **Planner** | PocketFlow | Decomposes the user query into claims and seed search queries | `claims`, `seed_queries` |
| **Searcher** | smolagents | Parallel Tavily + DuckDuckGo search | `hits`, `errors` |
| **Reader** | smolagents | Fetches URLs and extracts main text (trafilatura) | `pages` |
| **FactChecker** | LangGraph | Orchestrates search/read/LLM verify loop until evidence converges or search exhausts | `verified_claims`, `sources` |
| **Synthesizer** | Pydantic AI | Structured report from verified claims + citations | `ReportOutput` → markdown |

**Orchestration**: `workflow/coordinator.py` — `run_research_async` / `run_research_sync` drive the pipeline via `A2AClient` and `AgentRegistry`.  
**A2A**: `a2a_research.a2a` — role-scoped `AgentExecutor` registration, agent cards, in-process task store.  
**Evidence**: `a2a_research.tools` — `web_search`, `fetch_and_extract`.  
**UI**: Mesop web app (`src/a2a_research/ui/app.py`).

---

## Quick Start

```bash
# 1. Install dependencies (use make dev to also setup pre-commit hooks)
make install
# Or: uv sync --all-groups

# 2. Configure credentials
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
# Edit .env — set LLM_API_KEY, optional TAVILY_API_KEY for better search

# 3. Start the Mesop UI
make mesop
# Or: uv run mesop src/a2a_research/ui/app.py
# Opens at http://localhost:32123

# Run tests (no API key required for unit tests)
make test
# Or: uv run pytest
```

---

## Configuration (`.env`)

All settings are environment variables. The LLM stack is **provider-agnostic** (same `LLM_*` keys drive Planner, FactChecker, Searcher/Reader hosts, and the Pydantic AI Synthesizer).

### LLM Provider

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | Vendor: `openrouter`, `openai`, `anthropic`, `google`, `ollama` | `openrouter` |
| `LLM_MODEL` | Model name (provider-specific) | `openrouter/elephant-alpha` |
| `LLM_BASE_URL` | OpenAI-compatible base URL (OpenRouter/Ollama); optional for native Anthropic/Google | see `.env.example` |
| `LLM_API_KEY` | API key for your chosen provider | _(required for cloud)_ |

### Web search & research loop

| Variable | Description | Default |
|---|---|---|
| `TAVILY_API_KEY` | Tavily API key; blank = DuckDuckGo-only search | _(empty)_ |
| `SEARCH_MAX_RESULTS` | Per-provider hit cap (Tavily + DDG merged) | `5` |
| `RESEARCH_MAX_ROUNDS` | Max FactChecker loop rounds | `3` |
| `WORKFLOW_TIMEOUT` | Coordinator timeout (seconds) | `180` |

### Application

| Variable | Description | Default |
|---|---|---|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `MESOP_PORT` | Mesop web server port | `32123` |

### Provider Setup Examples

**OpenRouter** (default):
```bash
LLM_PROVIDER=openrouter
LLM_MODEL=openrouter/elephant-alpha
LLM_API_KEY=sk-or-...
```

**OpenAI**:
```bash
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
LLM_API_KEY=sk-...
```

**Ollama** (local, no API key):
```bash
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
LLM_BASE_URL=http://localhost:11434/v1
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_API_KEY=
```

**Anthropic**:
```bash
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-20250514
LLM_API_KEY=sk-ant-...
```

---

## Data Flow

### 1. Research pipeline (web evidence)

```
User query
  │
  ▼
Planner ──► LLM ──► claims + seed_queries
  │
  ▼
FactChecker (LangGraph loop)
  │     Searcher ──► Tavily + DDG ──► URLs
  │     Reader ──► fetch + trafilatura ──► page text
  │     Verify ──► LLM ──► verdicts / follow-up queries
  │     (repeat until converged, max rounds, or search exhausted)
  │
  ▼
Synthesizer ──► LLM (structured) ──► ReportOutput → markdown
```

Planner, FactChecker verification, and Synthesizer call `get_llm()` in `providers.py`. Searcher/Reader use smolagents with OpenAI-compatible models from the same `LLM_*` settings.

### 2. Workflow entrypoints

Public API:

```python
from a2a_research.workflow import run_research_sync, run_research_async
```

Implementation lives in `src/a2a_research/workflow/coordinator.py` (linear coordinator over `A2AClient`). Older PocketFlow builder/adapter modules may still exist for experiments; the Mesop UI and tests target `run_research_async`.

### 3. UI

The Mesop app exposes five sections:

- **Query input** — textarea at the bottom; submitting triggers the full pipeline
- **Agent timeline** — per-role card for Planner, Searcher, Reader, FactChecker, Synthesizer (PENDING → RUNNING → COMPLETED/FAILED)
- **Verified claims** — verdict badges (✅ SUPPORTED / ❌ REFUTED / ⚠️ INSUFFICIENT_EVIDENCE / …), confidence, sources, snippets
- **Sources panel** — deduplicated URLs from the FactChecker
- **Final report** — markdown from the Synthesizer (`session.final_report`)

`ResearchSession` is the source of truth for timeline, errors, and outputs.

---

## Project Structure

```
src/a2a_research/
├── agents/          # Planner (pocketflow), Searcher/Reader (smolagents), FactChecker (langgraph), Synthesizer (pydantic_ai)
├── a2a/             # AgentRegistry, A2AClient, agent cards, task helpers
├── workflow/        # run_research_* coordinator
├── tools/           # web_search, fetch_and_extract
├── models/          # ResearchSession, Claim, AgentRole, ReportOutput, WebSource, …
├── providers.py     # get_llm() — shared LLM vendor abstraction
├── ui/              # Mesop web app (app.py, components, …)
└── settings.py      # pydantic-settings (`LLM_*`, Tavily, timeouts, …)

data/corpus/         # Optional sample markdown (not used by the default web pipeline)
tests/               # Pytest suite (no API key required for unit tests)
```

---

## Example Chat Agent Scaffolds (other frameworks)

`src/a2a_research/agents/` also ships three reference **basic chat agents** built on alternative frameworks — not wired into the research pipeline by default, but ready to be registered as A2A handlers when you want to experiment with a different runtime.

| Folder | Framework | Canonical primitive | Highlight |
|---|---|---|---|
| `agents/langgraph/` | [LangGraph](https://github.com/langchain-ai/langgraph) | `StateGraph` + `MessagesState` + `InMemorySaver` | Multi-turn memory via `thread_id=session.id` |
| `agents/pydantic_ai/` | [Pydantic AI](https://github.com/pydantic/pydantic-ai) | `Agent(model, instructions=…)` with `OpenAIChatModel` | Typed, `deps_type` for request-scoped context |
| `agents/smolagents/` | [smolagents](https://github.com/huggingface/smolagents) | `ToolCallingAgent(tools=[], …)` with `OpenAIServerModel` | No Python execution; see folder README for the `CodeAgent` security note |

Each folder exposes the same surface:

```python
from a2a_research.agents.langgraph import chat_invoke  # or pydantic_ai / smolagents
from a2a_research.models import ResearchSession

session = ResearchSession(query="What is RAG?")
result = chat_invoke(session)
print(result.raw_content)
```

Run the standalone CLI demo per framework:

```bash
uv run python -m a2a_research.agents.langgraph   "hi"
uv run python -m a2a_research.agents.pydantic_ai "hi"
uv run python -m a2a_research.agents.smolagents  "hi"
```

Replace a default agent by registering an `AgentExecutor` factory (a zero-argument callable that returns a new executor instance from `a2a.server.agent_execution`):

```python
from a2a_research.a2a import register_executor_factory
from a2a_research.agents.pocketflow.planner.main import PlannerExecutor
from a2a_research.models import AgentRole

register_executor_factory(AgentRole.PLANNER, PlannerExecutor)
```

Use any class or zero-argument callable that produces an executor; the built-in defaults are registered from `a2a_research.a2a.registry._register_defaults`.

See each folder's `README.md` for framework-specific details (streaming hooks, multi-turn patterns, DI, and security notes).

---

## Demo Flow

```bash
# Start UI (ensure .env has LLM_API_KEY; optional TAVILY_API_KEY)
make mesop
# Open http://localhost:32123
```

### Programmatic Use

```python
from a2a_research.workflow import run_research_sync

session = run_research_sync("What is retrieval-augmented generation?")

print(session.final_report)

for claim in session.claims:
    print(f"{claim.verdict.value} ({claim.confidence:.0%}): {claim.text}")

print(session.error)
```

---

## Development

The project includes a self-documenting Makefile. Run `make` or `make help` to see all available commands:

```bash
$ make
  install         Install package with uv
  dev             Full dev setup: install + activate pre-commit hooks
  test            Run pytest suite with coverage
  watch           Run pytest in watch mode (re-runs on file changes)
  lint            Run ruff linter
  format          Format code with ruff
  format-check    Check formatting without modifying files
  typecheck       Run mypy type checker
  typecheck-ty    Run ty type checker
  check           Run all quality checks (no tests)
  all             Run tests + all quality checks (CI-ready)
  clean           Remove build artifacts and cache directories
  mesop           Start Mesop UI (with MESOP_STATE_SESSION_BACKEND=memory)
  htmlcov         Generate HTML coverage report
```

### Common Workflows

**Setup for development:**
```bash
make dev           # Install + activate pre-commit hooks
```

**During development:**
```bash
make test          # Run tests
make watch         # Run tests in watch mode (TDD)
```

**Before committing:**
```bash
make check         # Run lint + typecheck + format-check (fast)
make all           # Run everything including tests (CI-ready)
```

**Run the UI:**
```bash
make mesop         # Start the Mesop UI dev server
```

### Direct Commands

You can also run tools directly without Make:

```bash
uv run ruff check src/ tests/     # lint
uv run ruff format src/ tests/    # format
uv run mypy src/                  # type check (strict py311)
uv run ty check src/              # type check with ty
uv run pytest                     # run test suite
```

### Pre-commit Hooks

Install pre-commit hooks to catch issues before pushing:

```bash
pre-commit install
```

### CI/CD

GitHub Actions runs linting, formatting checks, type checking, and tests on every push and pull request to `main`. See `.github/workflows/ci.yml` for details.
