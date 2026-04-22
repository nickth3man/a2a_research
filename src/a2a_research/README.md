# a2a_research

Python package for the A2A Research system: a 5-agent, A2A-protocol-based research and verification pipeline.

## Package Purpose

This package contains the installable application code for the project. It provides:

- the backend research pipeline
- agent implementations and orchestration
- shared protocol/models/settings code
- the Mesop UI entrypoint and related interface logic

The system is designed around in-process A2A orchestration using `a2a-sdk` and environment-driven configuration.

## High-Level Pipeline

```text
Planner (PocketFlow)
  → FactChecker (LangGraph StateGraph loop)
      ↔ Searcher (smolagents + Tavily + DuckDuckGo)
      ↔ Reader (smolagents + trafilatura)
  → Synthesizer (Pydantic AI, structured report output)
```

## Subpackages

### `backend/`
The core implementation layer for the research pipeline. This includes:

- agent services
- shared models and utilities
- A2A protocol code
- workflow orchestration
- LLM provider integration
- external tool bindings

### `ui/`
The Mesop web UI used to interact with the pipeline visually.

## Top-Level Entrypoints

Common entrypoints exposed by this package include:

- `a2a_research.workflow.run_research_sync` — run the pipeline for a query
- `a2a_research.ui.app` — Mesop web UI
- `a2a_research.a2a` — registry and client for agent-to-agent dispatch

## Configuration

Configuration is environment-driven. See:

- `a2a_research.settings`
- `.env.example`

## Development Notes

- Target runtime: Python 3.11+
- Type hints are required
- Use absolute imports from `a2a_research`
- Package metadata lives in `a2a_research.__init__`
- The package is marked with `py.typed` for type checker support
