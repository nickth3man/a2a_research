# a2a_research

A 5-agent A2A (Agent-to-Agent) research and verification pipeline. The system performs multi-agent research with fact-checking, using HTTP-orchestrated agents backed by OpenRouter.

## Architecture Overview

The pipeline runs five specialized agents across different frameworks:

```text
Planner (PocketFlow)
  -> FactChecker (LangGraph)
      <-> Searcher (smolagents + Tavily/Brave/DuckDuckGo)
      <-> Reader (smolagents + trafilatura)
  -> Synthesizer (Pydantic AI, structured report output)
```

- **Planner** — breaks the research query into a plan
- **Searcher** — finds web sources
- **Reader** — fetches and extracts article content
- **FactChecker** — verifies claims in a loop with search and read support
- **Synthesizer** — produces the final structured report

The system offers two UIs:

- **Mesop UI** — Python-based web interface (`make mesop`)
- **React frontend** — TypeScript + Vite application in `frontend/` (`make frontend-dev`)

## Quick Start

```bash
# Install dependencies
make install

# Run tests
make test

# Start the Mesop UI
make mesop

# Start all agent services
make serve-all
```

## Project Structure

| Directory | Purpose |
|-----------|---------|
| `src/a2a_research/` | Main Python package |
| `src/a2a_research/backend/` | Core backend (agents, workflow, LLM, tools) |
| `src/a2a_research/ui/` | Mesop web application |
| `frontend/` | React + TypeScript + Vite frontend |
| `tests/` | Test suite |
| `scripts/` | Utility scripts |
| `static/` | Static web assets |

## Development

This project uses Python 3.11+ and `uv` for package management.

### Setup

```bash
make dev    # Full dev setup (install + pre-commit hooks)
```

### Common Commands

```bash
make test              # Run pytest suite (excludes live API tests)
make test-live-brave   # Run Brave live API tests (requires BRAVE_LIVE=1 + real key)
make test-live-tavily  # Run Tavily live API tests (requires TAVILY_LIVE=1 + real key)
make test-live         # Run all live API tests
make lint              # Run ruff linter and auto-fix issues
make format            # Format code with ruff
make typecheck         # Run mypy type checker
make typecheck-ty      # Run ty type checker
make check             # Run all quality checks (no tests)
make all               # Run tests + all quality checks (CI-ready)
make watch             # Run pytest in watch mode
```

### Agent Services

```bash
make serve-all              # Start all agent HTTP services
make serve-planner          # Start Planner service (port 10001)
make serve-searcher         # Start Searcher service (port 10002)
make serve-reader           # Start Reader service (port 10003)
make serve-fact-checker     # Start FactChecker service (port 10004)
make serve-synthesizer      # Start Synthesizer service (port 10005)
```

### Frontends

**Mesop UI:**
```bash
make mesop    # Start Mesop dev server (default http://localhost:32123)
```

**React frontend:**
```bash
make frontend-install   # Install frontend dependencies
make frontend-dev       # Start Vite dev server (proxies /api to localhost:8000)
make frontend-build     # Build production bundle
make frontend-lint      # Lint frontend code
```

## Configuration

Copy `.env.example` to `.env` and fill in your API keys:

- `LLM_API_KEY` — Required for LLM inference (OpenRouter key)
- `LLM_BASE_URL` — OpenAI-compatible endpoint (default: OpenRouter)
- `LLM_MODEL` — Model identifier (default: `openrouter/elephant-alpha`)
- `TAVILY_API_KEY` — For Tavily search integration
- `BRAVE_API_KEY` — For Brave search integration

Each agent service runs on its own port (10001-10005 by default). See `.env.example` for the full list of configuration options, including workflow tuning, telemetry, and budget limits.

## Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Python package configuration and tool settings |
| `Makefile` | Build automation and common commands |
| `AGENTS.md` | OpenCode agent instructions |
| `CONTRIBUTING.md` | Contribution guidelines and architecture notes |
| `uv.lock` | Locked dependency versions |

## Tools and Quality

- **Linting/Formatting:** ruff
- **Type Checking:** mypy (strict mode), ty
- **Testing:** pytest with coverage
- **Pre-commit:** Configured via `.pre-commit-config.yaml`

## License

MIT
