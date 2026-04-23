# a2a-research

A multi-agent A2A research and verification pipeline. The backend is built with Python and FastAPI, using multiple agent frameworks (PocketFlow, LangGraph, Pydantic AI, and smolagents) orchestrated over HTTP. The frontend is a React + Vite + TypeScript application.

## Stack

- **Backend:** Python 3.11+, FastAPI, uv (package manager), hatchling (build)
- **Agent frameworks:** PocketFlow, LangGraph, Pydantic AI, smolagents
- **Frontend:** React 19, Vite 8, TypeScript 6, ESLint 9
- **Testing:** pytest, ruff, mypy, ty

## Quick Start

1. **Install dependencies and activate dev tools**
   ```bash
   make dev
   ```

2. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys (OpenRouter, Tavily, Brave, etc.)
   ```

3. **Run tests**
   ```bash
   make test
   ```

4. **Start the backend**
   ```bash
   make serve
   ```

5. **Start the frontend** (in a separate terminal)
   ```bash
   make frontend-dev
   ```

The unified backend runs on `http://localhost:8000` and the Vite dev server starts on its default port (usually `http://localhost:5173`).

## Makefile Commands

### Setup

| Command | Description |
|---------|-------------|
| `make install` | Install Python package with uv |
| `make dev` | Full dev setup (install + pre-commit hooks) |
| `make frontend-install` | Install frontend dependencies |

### Development Servers

| Command | Description |
|---------|-------------|
| `make serve` | Start unified backend (FastAPI + all agents on port 8000) |
| `make serve-all` | Start all agent services on separate ports (standalone mode) |
| `make frontend-dev` | Start Vite dev server for the React frontend |
| `make frontend-build` | Build production frontend bundle |

### Quality & Testing

| Command | Description |
|---------|-------------|
| `make test` | Run pytest suite (excludes live API integration tests) |
| `make watch` | Run pytest in watch mode |
| `make lint` | Run ruff linter and auto-fix issues |
| `make format` | Format code with ruff |
| `make typecheck` | Run mypy type checker |
| `make typecheck-ty` | Run ty type checker |
| `make check` | Run all quality checks (lint + typecheck + typecheck-ty + format-check) |
| `make all` | Run tests + all quality checks (CI-ready) |
| `make frontend-lint` | Lint frontend code |

### Live API Tests

| Command | Description |
|---------|-------------|
| `make test-live-brave` | Run Brave live API tests |
| `make test-live-tavily` | Run Tavily live API tests |
| `make test-live` | Run all live API tests |

### Utilities

| Command | Description |
|---------|-------------|
| `make clean` | Remove build artifacts and cache directories |
| `make htmlcov` | Generate HTML coverage report |

## Service & Port Topology

By default, all agents are mounted on the unified backend:

- **Backend:** `http://localhost:8000`
  - Planner: `/agents/planner`
  - Searcher: `/agents/searcher`
  - Reader: `/agents/reader`
  - FactChecker: `/agents/fact-checker`
  - Synthesizer: `/agents/synthesizer`

When running standalone (`make serve-all`), each agent runs on its own port:

- Planner: `10001`
- Searcher: `10002`
- Reader: `10003`
- FactChecker: `10004`
- Synthesizer: `10005`

## Frontend / Backend Workflow

- The **backend** (`src/a2a_research/backend/`) exposes a FastAPI application that coordinates the multi-agent pipeline.
- The **frontend** (`frontend/`) is a standard Vite + React app that communicates with the backend.
- Both can be started independently during development.

## Environment Setup

Copy `.env.example` to `.env` and fill in at least:

- `LLM_API_KEY` — OpenRouter or other OpenAI-compatible API key
- `TAVILY_API_KEY` — Tavily search API key
- `BRAVE_API_KEY` — Brave Search API key

The `.env.example` file documents all available configuration options, including workflow settings (`WF_*` variables), agent ports, and telemetry toggles.

## Repo Structure

```
.
├── src/a2a_research/          # Python source
│   └── backend/               # FastAPI app, agents, workflow, models
├── frontend/                  # React + Vite + TypeScript frontend
├── tests/                     # pytest test suite
├── Makefile                   # Dev commands
├── pyproject.toml             # Python project config (uv + hatchling)
├── .env.example               # Environment variable template
└── CONTRIBUTING.md            # Detailed contributor guide
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the full development workflow, code conventions, and architecture notes.

## License

MIT
