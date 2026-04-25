# a2a-research

A multi-agent A2A research and verification pipeline. The backend is built with Python and FastAPI, using multiple agent frameworks (PocketFlow, LangGraph, Pydantic AI, and smolagents) orchestrated over HTTP. The frontend is a React + Vite + TypeScript application.

## Stack

- **Backend:** Python 3.11+, FastAPI, uv (package manager), hatchling (build)
- **Agent frameworks:** PocketFlow, LangGraph, Pydantic AI, smolagents
- **Frontend:** React 19, Vite 8, TypeScript 6, ESLint 9
- **Monorepo:** pnpm workspaces, Turborepo
- **Testing:** pytest, ruff, mypy, ty

## Quick Start

1. **Install all workspace dependencies**
   ```bash
   pnpm install
   ```

2. **Install Python dependencies**
   ```bash
   cd apps/api
   uv sync --all-groups
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys (OpenRouter, Tavily, Brave, etc.)
   ```

4. **Run tests**
   ```bash
   turbo run test
   ```

5. **Start the API and frontend**
   ```bash
   turbo run dev
   ```

The API runs on `http://localhost:8000` and the Vite dev server starts on `http://localhost:5173`.

## Turbo Commands

### Development

| Command | Description |
|---------|-------------|
| `pnpm install` | Install all workspace dependencies |
| `turbo run dev` | Start API and frontend concurrently |
| `turbo run build` | Build frontend |
| `turbo run generate` | Generate TypeScript client from OpenAPI spec |

### Quality & Testing

| Command | Description |
|---------|-------------|
| `turbo run test` | Run Python test suite |
| `turbo run lint` | Run ruff (Python) + eslint (frontend) |
| `pnpm e2e:install` | One-time: download Playwright Chromium browser |
| `pnpm e2e` | Run Playwright end-to-end tests (auto-starts API + web) |

### Python-specific (from `apps/api/`)

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run pytest suite with coverage |
| `uv run ruff check src/ tests/` | Run ruff linter |
| `uv run ruff format src/ tests/` | Format code with ruff |
| `uv run mypy src/` | Run mypy type checker |
| `uv run uvicorn entrypoints.api:app --reload` | Start API server |

## Service & Port Topology

All 12 agents are mounted on the unified backend (`turbo run dev`):

| Agent | Mount path | Framework |
|-------|-----------|-----------|
| Preprocessor | `/agents/preprocessor` | stub |
| Clarifier | `/agents/clarifier` | PocketFlow |
| Planner | `/agents/planner` | PocketFlow |
| Searcher | `/agents/searcher` | smolagents |
| Ranker | `/agents/ranker` | stub |
| Reader | `/agents/reader` | smolagents |
| Evidence Deduplicator | `/agents/evidence-deduplicator` | stub |
| Fact Checker | `/agents/fact-checker` | LangGraph |
| Adversary | `/agents/adversary` | stub |
| Synthesizer | `/agents/synthesizer` | Pydantic AI |
| Critic | `/agents/critic` | stub |
| Postprocessor | `/agents/postprocessor` | stub |

## Frontend / Backend Workflow

- The **backend** (`apps/api/`) exposes a FastAPI application that coordinates the multi-agent pipeline.
- The **frontend** (`apps/web/`) is a standard Vite + React app that communicates with the backend through a small SSE/fetch service layer.
- The **contracts** (`packages/contracts/`) package provides a typed SDK generated from the backend's OpenAPI spec.
- Both API and frontend can be started together with `turbo run dev` or independently.

## Environment Setup

Copy `.env.example` to `.env` and fill in at least:

- `LLM_API_KEY` — OpenRouter or other OpenAI-compatible API key
- `TAVILY_API_KEY` — Tavily search API key
- `BRAVE_API_KEY` — Brave Search API key

Optional gateway hardening settings:

- `API_KEY` — shared key for `/api/research` endpoints; leave blank for local unauthenticated development
- `VITE_API_KEY` — browser-visible copy of `API_KEY`; required by the Vite frontend when `API_KEY` is set
- `MAX_CONCURRENT_SESSIONS` — per-process cap for active research workflows
- `SESSION_TTL_SECONDS` — time before abandoned sessions are pruned

The `.env.example` file documents all available configuration options, including workflow settings (`WF_*` variables), agent ports, and telemetry toggles.

## Repo Structure

```
.
├── apps/
│   ├── api/                    # Python backend (FastAPI)
│   │   ├── agents/              # Agent implementations
│   │   ├── core/                # Core models, settings, logging
│   │   ├── entrypoints/         # FastAPI app and launcher
│   │   ├── llm/                 # LLM provider integrations
│   │   ├── tools/               # Search and fetch utilities
│   │   ├── workflow/             # Research workflow engine
│   │   ├── tests/              # pytest test suite
│   │   ├── pyproject.toml      # Python project config
│   │   └── package.json        # Turborepo task scripts
│   └── web/                    # React frontend (Vite)
│       ├── src/                # React + TypeScript source
│       └── package.json        # Frontend dependencies
├── packages/
│   └── contracts/              # Auto-generated TypeScript client
│       ├── src/                # Generated SDK from OpenAPI
│       └── package.json        # @hey-api/openapi-ts codegen
├── turbo.json                  # Turborepo pipeline config
├── pnpm-workspace.yaml         # Workspace package definitions
├── package.json                # Root workspace config
├── pyproject.toml              # Root uv workspace config
├── .env.example                # Environment variable template
└── CONTRIBUTING.md             # Detailed contributor guide
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow, code conventions, and architecture notes.

## License

MIT
