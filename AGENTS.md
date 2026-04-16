# AGENTS.md

High-signal guidance for working in this repo. If a fact is obvious from filenames or generic Python conventions, it’s omitted.

---

## Developer commands

Use `uv` for everything. The project is managed with `pyproject.toml` + `uv.lock`.

```bash
# Full dev setup (install + pre-commit hooks)
make dev

# Or install only (no hooks):
uv sync --all-groups

# Verification pipeline (run these in order)
make check        # lint + format-check + mypy + ty
make test         # pytest with coverage and auto-parallel (-n auto)

# Direct equivalents
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run ty check src/
uv run pytest
```

- CI runs on Python 3.11 and 3.12 and executes the exact same four checks as `make check` plus tests.
- pytest defaults (from `pyproject.toml`) include `-n auto --cov=src/a2a_research --cov-report=term-missing`.

---

## Source layout & entrypoints

- Package root: `src/a2a_research/`
- Main modules:
  - `workflow/` — PocketFlow runtime (`run_research_sync` is the stable public entrypoint)
  - `a2a/` — In-process A2A registry, server, and client facades
  - `agents/` — Agent invoke functions (researcher, analyst, verifier, presenter)
  - `rag/` — ChromaDB ingestion and retrieval
  - `ui/` — Mesop web app (`app.py` is the page entrypoint)
  - `models/` — Pydantic domain types
  - `prompts/` — System prompt strings
  - `helpers/` — Deterministic formatting/reporting utilities

---

## Adding a new agent

If you add an agent role, you must register it in **four** places:
1. `a2a/__init__.py` — register the handler callable
2. `models/__init__.py` — add the role enum/value
3. `prompts/__init__.py` — add the system prompt
4. `workflow/builder.py` — wire the role into the pipeline

---

## Type-checking quirks

- mypy runs in **strict** mode (`mypy.ini`), but three areas are explicitly relaxed:
  - `a2a_research.ui.*` — untyped defs/decorators/calls allowed
  - `a2a_research.workflow.*` — untyped defs/calls allowed; `type-arg` ignored
  - `a2a_research.helpers` — same relaxations as workflow
- `pocketflow.*` is entirely ignored by mypy.
- `ty` is also run in CI; it must pass independently of mypy.

---

## Testing conventions

- Unit tests **require no API key** — all LLM calls are mocked.
- UI tests rely on fixtures in `tests/conftest.py` that stub Mesop’s component runtime.
- Run a single test file: `uv run pytest tests/test_workflow.py`
- Run a single test: `uv run pytest tests/test_workflow.py::test_name -v`

---

## Debugging

When investigating runtime errors or unexpected agent behaviour, read `/logs` first — it contains the most recent application output and is the fastest way to locate the failing component before diving into source.

---

## UI & RAG runtime quirks

- **Mesop dev server**: `make mesop` sets `MESOP_STATE_SESSION_BACKEND=memory` to avoid state-desync errors on hot reload. UI listens on `http://localhost:32123` by default.
- **RAG corpus**: markdown files live in `data/corpus/`. Ingest with `make ingest` (idempotent; skips if already populated, force with `ingest_corpus(force=True)`).
- **ChromaDB storage**: `data/chroma/` is gitignored and created automatically.

---

## Environment & configuration

- Settings are loaded via `pydantic-settings` from `.env` automatically.
- Default `.env.example` uses **OpenRouter** (`LLM_PROVIDER=openrouter`, `LLM_MODEL=openrouter/elephant-alpha`).
- Provider-agnostic design: LLM and embedding providers can differ (`openrouter`, `openai`, `anthropic`, `google`, `ollama`).

---

## External tools

When you need docs or examples beyond the repo, prefer these tools:

- **`searchGitHub`** — Search public GitHub for production usage patterns of unfamiliar APIs or libraries.
- **`read_wiki_structure`** / **`read_wiki_contents`** — Map and read docs from a GitHub repository.
- **`ask_question`** — Ask a synthesized, context-grounded question about a GitHub repository.
- **`tavily-search`** — Current best practices, changelogs, and troubleshooting.
- **`tavily-crawl`** / **`tavily-extract`** — Deep documentation dives or raw page content.
