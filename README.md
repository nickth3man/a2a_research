# A2A Research — Local-First 4-Agent Research System

**A research-and-verification pipeline** orchestrated by a modular PocketFlow runtime. Four agents — Researcher, Analyst, Verifier, Presenter — communicate through an in-process A2A client/server layer, with a registry-driven workflow that can be extended with new agents and alternate pipeline orderings without rewriting the orchestration core. The system ingests a local RAG corpus, decomposes user queries into verifiable claims, checks evidence, and renders a structured markdown report.

---

## Architecture

```
Researcher ──► Analyst ──► Verifier ──► Presenter
    │                                    │
    └──── PocketFlow AsyncFlow + A2A ───┘
```

| Agent | Role | Output |
|---|---|---|
| **Researcher** | Retrieves relevant chunks from the ChromaDB RAG corpus | `chunks + summary + citations` |
| **Analyst** | Decomposes the query into atomic verifiable claims | `atomic claims list` |
| **Verifier** | Assigns SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE verdicts | `verified claims with confidence` |
| **Presenter** | Renders the final structured markdown report | `markdown report` |

**Orchestration**: PocketFlow `AsyncFlow` + `AsyncNode` wrappers in `workflow/`.  
**A2A Contracts**: In-process `A2AClient` → `A2AServer` dispatch with typed `A2AMessage` / `AgentResult` payloads, plus extensible envelope / policy / artifact models.  
**RAG**: ChromaDB with sentence-chunked markdown corpus; semantic similarity retrieval.  
**PocketFlow**: The bundled `pocketflow_reference` runtime powers both deterministic helper flows and the main research workflow runtime.  
**UI**: Mesop web app (`src/a2a_research/ui/app.py`).

---

## Quick Start

```bash
# 1. Install dependencies with uv
uv pip install -e .

# 2. Configure credentials
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
# Edit .env — set LLM_API_KEY and any provider-specific values

# 3. Ingest the RAG corpus (one-time; idempotent — safe to re-run)
uv run python -c "from a2a_research.rag import ensure_corpus_ingested; print(f'Ingested {ensure_corpus_ingested()} chunks')"

# 4. Start the Mesop UI
uv run mesop src/a2a_research/ui/app.py
# Opens at http://localhost:32123

# Run tests (no API key required for unit tests)
uv run pytest
```

---

## Configuration (`.env`)

All settings are environment variables. The system is **provider-agnostic** — pick your LLM and embedding provider independently.

### LLM Provider

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | Vendor: `openai`, `anthropic`, `google`, `ollama` | `openai` |
| `LLM_MODEL` | Model name (provider-specific) | `gpt-4o-mini` |
| `LLM_BASE_URL` | OpenAI-compatible base URL override (blank = provider default) | _(empty)_ |
| `LLM_API_KEY` | API key for your chosen provider | _(required)_ |

### Embeddings

| Variable | Description | Default |
|---|---|---|
| `EMBEDDING_MODEL` | Embedding model name | `text-embedding-3-small` |
| `EMBEDDING_PROVIDER` | Embedding vendor: `openai`, `ollama` | `openai` |
| `EMBEDDING_BASE_URL` | Separate base URL for embeddings (blank = same as LLM_BASE_URL) | _(empty)_ |
| `EMBEDDING_API_KEY` | Embedding API key (blank = same as LLM_API_KEY) | _(empty)_ |

### Vector Store (ChromaDB)

| Variable | Description | Default |
|---|---|---|
| `CHROMA_PERSIST_DIR` | Persistent storage directory for ChromaDB | `data/chroma` |
| `CHROMA_COLLECTION` | Collection name | `a2a_research` |

### Chunking

| Variable | Description | Default |
|---|---|---|
| `CHUNK_SIZE` | Target chunk size in characters (sentence-boundary aware) | `512` |
| `CHUNK_OVERLAP` | Character overlap between adjacent chunks | `64` |

### Application

| Variable | Description | Default |
|---|---|---|
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `MESOP_PORT` | Mesop web server port | `32123` |

### Provider Setup Examples

**OpenAI** (default):
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

### 1. Ingestion

```python
from a2a_research.rag import ingest_corpus
count = ingest_corpus()  # idempotent
```

Reads all `.md` files from `data/corpus/`, splits on sentence boundaries with `CHUNK_SIZE` / `CHUNK_OVERLAP`, embeds via the configured provider, and upserts into ChromaDB. Re-running when the collection is already populated is safe (skips by default, force with `ingest_corpus(force=True)`).

### 2. Research Pipeline

```
User query
  │
  ▼
Researcher ──► ChromaDB similarity search ──► chunks, ranked sources, summary
  │
  ▼
Analyst ──► LLM decomposition ──► atomic claims
  │
  ▼
Verifier ──► LLM verdict + confidence ──► verified claims (SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE)
  │
  ▼
Presenter ──► LLM synthesis ──► structured markdown report
```

All LLM calls route through the shared `get_llm()` provider abstraction in `providers.py`. Swapping providers requires only `.env` changes, assuming the relevant optional provider package is installed.

### 2.5. Modular Workflow Runtime

The main execution path now lives in `src/a2a_research/workflow/`:

- `nodes.py` — PocketFlow `ActorNode` wrappers that invoke agents through the A2A layer
- `builder.py` — declarative workflow builder for assembling an ordered role pipeline
- `coordinator.py` — orchestration entrypoint for the default four-agent flow
- `adapter.py` — sync/async compatibility adapter providing `invoke()` / `ainvoke()` interfaces
- `policy.py` — workflow policy primitives for future routing and constraint logic

The current default pipeline is still linear, but the runtime is now modular enough to:

- add a new agent by registering a new role/handler pair,
- change the workflow order without replacing the orchestration engine,
- use the stable `from a2a_research.workflow import run_research_sync` import path.

### 3. UI

The Mesop app exposes five sections:

- **Query input** — textarea at the bottom; submitting triggers the full pipeline
- **Agent timeline** — per-role card showing status (PENDING → RUNNING → COMPLETED/FAILED) and the agent's log message
- **Verified claims** — each claim shows verdict badge (✅ SUPPORTED / ❌ REFUTED / ⚠️ INSUFFICIENT_EVIDENCE), confidence percentage, sources, and evidence snippets
- **Sources panel** — deduplicated citation list with index numbers
- **Final report** — rendered markdown output from the Presenter agent

UI state now treats `ResearchSession` as the source of truth for progress and errors, so partially initialized sessions can render the timeline safely without being mistaken for final results.

---

## Project Structure

```
src/a2a_research/
├── agents/          # Agent invoke functions (researcher_invoke, analyst_invoke, verifier_invoke, presenter_invoke)
├── a2a/             # In-process A2A contracts and registry-backed server/client helpers
├── workflow/        # PocketFlow runtime (builder, actor nodes, coordinator, adapter, policy)
├── rag/             # ChromaDB ingestion and semantic retrieval
├── models/          # Pydantic domain types (ResearchSession, Claim, AgentResult, WorkflowState, Artifact, Envelope, Policy, …)
├── prompts/         # Per-agent system prompts (RESEARCHER_PROMPT, ANALYST_PROMPT, VERIFIER_PROMPT, PRESENTER_PROMPT)
├── helpers/         # Deterministic PocketFlow-style helpers (format_claim_verdict, build_markdown_report, …)
├── ui/              # Mesop web app
│   ├── __init__.py
│   ├── app.py       # Page definition, state class, event handlers
│   └── components.py # UI components (agent_timeline_card, claims_panel, sources_panel, report_panel, …)
└── settings.py      # Typed settings from environment variables (pydantic-settings)

data/corpus/         # Markdown files ingested into ChromaDB
data/chroma/        # Persistent ChromaDB storage (gitignored)
tests/              # Pytest suite (no API key required for unit tests)
```

---

## Demo Flow

```bash
# Ingest corpus (already done on first install)
uv run python -c "from a2a_research.rag import ingest_corpus; print(ingest_corpus())"

# Start UI
uv run mesop src/a2a_research/ui/app.py
# Open http://localhost:32123
```

### Programmatic Use

```python
from a2a_research.workflow import run_research_sync
from a2a_research.models import AgentRole

session = run_research_sync("What is RAG and how does it reduce hallucinations?")

# Rendered markdown report from Presenter
print(session.final_report)

# Structured verified claims from Verifier
for claim in session.get_agent(AgentRole.VERIFIER).claims:
    print(f"{claim.verdict.value} ({claim.confidence:.0%}): {claim.text}")

# Progress and failures live on the session too
print(session.error)
```

---

## Development

Use the provided Makefile for common tasks:

```bash
make install       # Install package with uv
make test          # Run pytest suite with coverage
make lint          # Run ruff linter
make format        # Run ruff formatter
make typecheck     # Run mypy (strict py311)
make typecheck-ty  # Run ty type checker
make check         # Run lint + format check + typecheck + ty
make mesop         # Start the Mesop UI dev server
make ingest        # Ingest the RAG corpus into ChromaDB
```

You can also run tools directly:

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
