# Contributing to A2A Research

Thank you for your interest in contributing! This document outlines the development workflow and conventions we follow.

## Repository Structure

This project is a **pnpm + Turborepo monorepo** with the following layout:

```
.
├── apps/
│   ├── api/              # Python backend (FastAPI)
│   │   ├── src/a2a_research/   # Python source code
│   │   ├── tests/              # pytest test suite
│   │   ├── pyproject.toml      # Python project config (uv + hatchling)
│   │   └── package.json        # Turborepo task scripts
│   └── web/              # React frontend (Vite)
│       ├── src/                # React + TypeScript source
│       ├── package.json        # Frontend dependencies
│       └── vite.config.ts      # Vite config with API proxy
├── packages/
│   └── contracts/        # Auto-generated TypeScript client from OpenAPI
│       ├── src/                # Generated SDK code
│       └── package.json        # @hey-api/openapi-ts codegen
├── turbo.json            # Turborepo pipeline config
├── pnpm-workspace.yaml   # Workspace package definitions
├── package.json          # Root workspace config
└── pyproject.toml        # Root uv workspace config
```

### Architecture Overview

- **`apps/api/`** — Python backend built with FastAPI. Contains the multi-agent pipeline, workflow orchestration, RAG, and all agent implementations. Uses `uv` for Python dependency management.
- **`apps/web/`** — React 19 + Vite 8 + TypeScript frontend. Communicates with the backend through a small SSE/fetch service layer.
- **`packages/contracts/`** — Auto-generated TypeScript SDK from the backend's OpenAPI spec. Available as the `@a2a/contracts` workspace package for typed API integrations.

## Development Setup

### Prerequisites

- **Node.js** v20+ and **pnpm** v10+ (package manager)
- **Python 3.11+** and **[uv](https://docs.astral.sh/uv/getting-started/installation/)** (Python package manager)

### Getting Started

1. **Clone the repository**

2. **Install all workspace dependencies**
   ```bash
   pnpm install
   ```
   This installs Node dependencies for the root, `apps/web/`, and `packages/contracts/`. Python dependencies are managed separately by `uv`.

3. **Install Python dependencies**
   ```bash
   cd apps/api
   uv sync --all-groups
   ```
   This installs runtime + `test` + `lint` dependency groups.

4. **Copy the environment template**
   ```bash
   cp .env.example .env
   # Edit .env and set your API keys
   ```

   If you set backend gateway auth with `API_KEY`, also set `VITE_API_KEY`
   to the same value so the Vite frontend can authenticate browser requests.

5. **Generate the TypeScript client** (requires the API to be running)
   ```bash
   turbo run generate
   ```

### Installing specific Python dependency groups

The project uses [PEP 735 dependency groups](https://peps.python.org/pep-0735/) to keep runtime and dev dependencies separate:

| Group | Contents | Install command |
|-------|----------|-----------------|
| _(runtime)_ | Core package deps | `uv sync` |
| `test` | pytest, hypothesis, coverage | `uv sync --group test` |
| `lint` | ruff, mypy, ty, pre-commit | `uv sync --group lint` |
| `dev` | all of the above | `uv sync --all-groups` |

## Running the Project

### Start everything (API + frontend)

```bash
turbo run dev
```

This runs the `dev` task across all workspace packages concurrently:
- `apps/api/` — FastAPI server on `http://localhost:8000`
- `apps/web/` — Vite dev server on `http://localhost:5173`

### Start individual services

```bash
# API only
cd apps/api && uv run uvicorn a2a_research.backend.entrypoints.api:app --reload

# Frontend only
cd apps/web && pnpm dev
```

## Code Quality

We use the following tools to maintain code quality:

- **Ruff** — linting and formatting (`turbo run lint`)
- **mypy** — static type checking in strict mode
- **ty** — additional type checking
- **pytest** — testing framework (`turbo run test`)

### Running quality checks

```bash
# Lint all packages
turbo run lint

# Run all tests
turbo run test

# Build frontend
turbo run build
```

For Python-specific checks:

```bash
cd apps/api
uv run ruff check src/ tests/    # Lint
uv run ruff format src/ tests/   # Format
uv run mypy src/                 # Type check
uv run pytest                    # Tests
```

### Pre-commit Hooks

Pre-commit hooks are installed automatically. To install or reinstall them manually:

```bash
cd apps/api
uv run pre-commit install
```

Hooks run ruff (lint + format), mypy, and ty on every commit.

## Running Tests

All tests pass without requiring an API key (LLM calls are mocked):

```bash
turbo run test
```

Or run Python tests directly:

```bash
cd apps/api
uv run pytest
```

For TDD with automatic re-runs on file changes:

```bash
cd apps/api
uv run pytest-watch
```

For coverage reporting only:

```bash
cd apps/api
uv run pytest --cov=src/a2a_research
```

## Generating the TypeScript Client

The `packages/contracts/` package auto-generates a TypeScript SDK from the backend's OpenAPI spec:

```bash
# Start the API first, then:
turbo run generate
```

This runs `openapi-ts` in `packages/contracts/`, producing typed client code in `packages/contracts/src/`. The generated package is available to workspace apps via the `@a2a/contracts` dependency.

## Project Conventions

- **Python 3.11+** is required
- **Type annotations** are required for all public functions
- **mypy strict mode** is enforced (see `apps/api/pyproject.toml`)
- **Docstrings** should be concise; module-level docstrings are fine, but avoid redundant inline comments
- Follow the existing **feature-based structure** under `apps/api/src/a2a_research/`
- **pnpm** is the package manager (not npm)
- **Turborepo** orchestrates cross-package tasks

## Pull Request Process

1. Ensure all checks pass: `turbo run lint`
2. Ensure tests pass: `turbo run test`
3. Ensure frontend builds: `turbo run build`
4. Update documentation if your change affects public APIs or configuration
5. Open a PR against the `main` branch

## Architecture Notes

### Backend (`apps/api/`)

- **`a2a/`** — In-process A2A contract layer (messages, agent cards, server/client)
- **`workflow/`** — PocketFlow runtime (nodes, flows, builders, coordinators)
- **`agents/`** — Agent invocation functions
- **`rag/`** — ChromaDB ingestion and retrieval
- **`models/`** — Shared Pydantic domain types

If you add a new agent, you must register it in **four** places:
1. Register its handler in `a2a/__init__.py`
2. Add its role to `models/__init__.py` (if new)
3. Add prompts to `prompts/__init__.py`
4. Wire it into the workflow builder in `workflow/builder.py`

### Frontend (`apps/web/`)

- Standard React + Vite + TypeScript application
- Imports typed client from `@a2a/contracts` workspace package
- Vite proxies `/api` requests to `http://localhost:8000`

### Contracts (`packages/contracts/`)

- Auto-generated TypeScript SDK from the backend's OpenAPI spec
- Generated via `@hey-api/openapi-ts`
- Consumed by `apps/web/` as `@a2a/contracts`
