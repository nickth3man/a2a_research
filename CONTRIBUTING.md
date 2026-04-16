# Contributing to A2A Research

Thank you for your interest in contributing! This document outlines the development workflow and conventions we follow.

## Development Setup

1. **Clone the repository**
2. **Install [uv](https://docs.astral.sh/uv/getting-started/installation/)** (the project's package manager)
3. **Run the full dev setup** (installs the package + all dev dependencies + pre-commit hooks):
   ```bash
   make dev
   ```
   This runs `uv sync --all-groups` to install runtime + `test` + `lint` dependency groups, then activates pre-commit hooks.
4. **Copy the environment template**:
   ```bash
   cp .env.example .env
   # Edit .env and set your API keys
   ```

### Installing specific dependency groups

The project uses [PEP 735 dependency groups](https://peps.python.org/pep-0735/) to keep runtime and dev dependencies separate:

| Group | Contents | Install command |
|-------|----------|-----------------|
| _(runtime)_ | Core package deps | `uv sync` |
| `test` | pytest, hypothesis, coverage | `uv sync --group test` |
| `lint` | ruff, mypy, ty, pre-commit | `uv sync --group lint` |
| `dev` | all of the above | `uv sync --all-groups` |

## Code Quality

We use the following tools to maintain code quality:

- **Ruff** — linting and formatting (`make lint`, `make format`)
- **mypy** — static type checking in strict mode (`make typecheck`)
- **ty** — additional type checking (`make typecheck-ty`)
- **pytest** — testing framework (`make test`)

Run all checks at once:

```bash
make check
```

### Pre-commit Hooks

Pre-commit hooks are installed automatically by `make dev`. To install or reinstall them manually:

```bash
uv run pre-commit install
```

Hooks run ruff (lint + format), mypy, and ty on every commit.

## Running Tests

All tests pass without requiring an API key (LLM calls are mocked):

```bash
make test
```

For TDD with automatic re-runs on file changes:

```bash
make watch
```

For coverage reporting only:

```bash
uv run pytest --cov=src/a2a_research
```

## Project Conventions

- **Python 3.11+** is required
- **Type annotations** are required for all public functions
- **mypy strict mode** is enforced (see `mypy.ini`)
- **Docstrings** should be concise; module-level docstrings are fine, but avoid redundant inline comments
- Follow the existing **feature-based structure** under `src/a2a_research/`

## Pull Request Process

1. Ensure all checks pass: `make check`
2. Ensure tests pass: `make test`
3. Update documentation if your change affects public APIs or configuration
4. Open a PR against the `main` branch

## Architecture Notes

- **`a2a/`** — In-process A2A contract layer (messages, agent cards, server/client)
- **`workflow/`** — PocketFlow runtime (nodes, flows, builders, coordinators)
- **`agents/`** — Agent invocation functions
- **`rag/`** — ChromaDB ingestion and retrieval
- **`ui/`** — Mesop web application
- **`models/`** — Shared Pydantic domain types

If you add a new agent, you must register it in **four** places:
1. Register its handler in `a2a/__init__.py`
2. Add its role to `models/__init__.py` (if new)
3. Add prompts to `prompts/__init__.py`
4. Wire it into the workflow builder in `workflow/builder.py`
