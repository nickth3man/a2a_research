# A2A Research — Local-First 4-Agent Research System

**A research-and-verification pipeline** orchestrated by LangGraph. Four agents — Researcher, Analyst, Verifier, Presenter — communicate through an in-process A2A client/server layer, while the bundled PocketFlow reference runtime powers deterministic report-building helpers. The system ingests a local RAG corpus, decomposes user queries into verifiable claims, checks evidence, and renders a structured markdown report.

---

## Architecture

```
Researcher ──► Analyst ──► Verifier ──► Presenter
    │                                    │
    └────────── LangGraph StateGraph ───┘
```

| Agent | Role | Output |
|---|---|---|
| **Researcher** | Retrieves relevant chunks from the ChromaDB RAG corpus | `chunks + summary + citations` |
| **Analyst** | Decomposes the query into atomic verifiable claims | `atomic claims list` |
| **Verifier** | Assigns SUPPORTED / REFUTED / INSUFFICIENT_EVIDENCE verdicts | `verified claims with confidence` |
| **Presenter** | Renders the final structured markdown report | `markdown report` |

**Orchestration**: LangGraph `StateGraph` with typed `WorkflowState` threaded through all nodes.  
**A2A Contracts**: In-process `A2AClient` → `A2AServer` dispatch with typed `A2AMessage` / `AgentResult` payloads.  
**RAG**: ChromaDB with sentence-chunked markdown corpus; semantic similarity retrieval.  
**PocketFlow**: The bundled `pocketflow_reference` runtime is used for deterministic helper flows such as markdown report assembly.  
**UI**: Mesop web app (`src/a2a_research/ui/app.py`).

---

## Quick Start

```bash
# 1. Create and activate virtual environment
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -e ".[dev]"

# 3. Configure credentials
# macOS/Linux: cp .env.example .env
# Windows PowerShell: Copy-Item .env.example .env
# Edit .env — set LLM_API_KEY and any provider-specific values

# 4. Ingest the RAG corpus (one-time; idempotent — safe to re-run)
python -c "from a2a_research.rag import ingest_corpus; print(f'Ingested {ingest_corpus()} chunks')"

# 5. Start the Mesop UI
mesop src/a2a_research/ui/app.py
# Opens at http://localhost:32123

# Run tests (no API key required for unit tests)
pytest
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

### 3. UI

The Mesop app exposes five sections:

- **Query input** — textarea at the bottom; submitting triggers the full pipeline
- **Agent timeline** — per-role card showing status (PENDING → RUNNING → COMPLETED/FAILED) and the agent's log message
- **Verified claims** — each claim shows verdict badge (✅ SUPPORTED / ❌ REFUTED / ⚠️ INSUFFICIENT_EVIDENCE), confidence percentage, sources, and evidence snippets
- **Sources panel** — deduplicated citation list with index numbers
- **Final report** — rendered markdown output from the Presenter agent

---

## Project Structure

```
src/a2a_research/
├── agents/          # Agent invoke functions (researcher_invoke, analyst_invoke, verifier_invoke, presenter_invoke)
├── a2a/             # In-process A2A contracts (A2AMessage, A2AClient, A2AServer)
├── graph/           # LangGraph StateGraph wiring; run_research_sync / run_research_async entrypoints
├── rag/             # ChromaDB ingestion and semantic retrieval
├── models/          # Pydantic domain types (ResearchSession, Claim, AgentResult, WorkflowState, …)
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
python -c "from a2a_research.rag import ingest_corpus; print(ingest_corpus())"

# Start UI
mesop src/a2a_research/ui/app.py
# Open http://localhost:32123

# Example query: "What is RAG and how does it reduce hallucinations?"
# Click "Run Research" — watch each agent turn green
# Review verified claims, sources, and final report
```

### Programmatic Use

```python
from a2a_research.graph import run_research_sync
from a2a_research.models import AgentRole

session = run_research_sync("What is RAG and how does it reduce hallucinations?")

# Rendered markdown report from Presenter
print(session.final_report)

# Structured verified claims from Verifier
for claim in session.get_agent(AgentRole.VERIFIER).claims:
    print(f"{claim.verdict.value} ({claim.confidence:.0%}): {claim.text}")
```

---

## Development

```bash
ruff check src/ tests/      # lint
ruff format src/ tests/      # format
mypy src/                    # type check (strict py311)
pytest                       # run test suite
```

### Installing Optional Provider Packages

```bash
pip install langchain-anthropic    # Anthropic models
pip install langchain-google-genai  # Google models
pip install langchain-ollama        # Ollama local models
```

If you stay on the default OpenAI-compatible path, `langchain-openai` is already installed through the base project dependencies.
