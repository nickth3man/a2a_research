# Contributing to A2A Research

Thank you for your interest in contributing! This document outlines the development workflow and conventions we follow.

## Development Setup

1. **Clone the repository**
2. **Create a virtual environment** (recommended)
3. **Install in development mode**:
   ```bash
   make install
   # or
   pip install -e ".[dev]"
   ```
4. **Copy the environment template**:
   ```bash
   cp .env.example .env
   # Edit .env and set your API keys
   ```

## Code Quality

We use the following tools to maintain code quality:

- **Ruff** — linting and formatting (`make lint`, `make format`)
- **mypy** — static type checking (`make typecheck`)
- **pytest** — testing framework (`make test`)

### Pre-commit Hooks

We recommend installing pre-commit hooks to catch issues before pushing:

```bash
pip install pre-commit
pre-commit install
```

This will run linting, formatting, and basic checks on every commit.

## Running Tests

All tests should pass without requiring an API key (we mock LLM calls in unit tests):

```bash
pytest
```

For coverage reporting:

```bash
pytest --cov=src/a2a_research
```

## Project Conventions

- **Python 3.11+** is required
- **Type annotations** are required for all public functions
- **mypy strict mode** is enforced
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

If you add a new agent, you must:
1. Register its handler in `a2a/__init__.py`
2. Add its role to `models/__init__.py` (if new)
3. Add prompts to `prompts/__init__.py`
4. Wire it into the workflow builder in `workflow/builder.py`
