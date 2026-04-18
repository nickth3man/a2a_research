# A2A Research

HTTP-split, 5-agent research and verification pipeline built on A2A, PocketFlow, smolagents, LangGraph, Pydantic AI, and Mesop.

## Overview

`a2a_research` takes a user query, breaks it into verifiable claims, gathers public web evidence, verifies those claims in a bounded loop, and produces a structured markdown report with citations.

The five agents are:

1. **Planner** — PocketFlow-based query decomposition
2. **Searcher** — smolagents tool-calling web search refinement
3. **Reader** — smolagents tool-calling page extraction
4. **FactChecker** — LangGraph verification loop coordinating Searcher + Reader
5. **Synthesizer** — Pydantic AI structured report generation

**Orchestration (two levels):** The coordinator issues **three** sequential HTTP calls: **Planner → Fact Checker → Synthesizer**. Searcher and Reader are **not** separate coordinator steps; the Fact Checker service runs a LangGraph loop that **invokes** Searcher and Reader over A2A whenever it needs web search or page text. The UI lists all five roles so the timeline can show search/read activity during verification.

## Architecture

```text
┌──────────────────────────────┐
│ Mesop UI                     │
│  - submit query              │
│  - drain ProgressQueue       │
│  - render timeline/report    │
└──────────────┬───────────────┘
               │ run_research_async()
               ▼
┌──────────────────────────────┐
│ Coordinator                  │
│  - HTTP A2A client           │
│  - session state             │
│  - timeout / error handling  │
└───────┬───────────┬──────────┘
        │           │
        ▼           ▼
   Planner      Synthesizer
   :10001       :10005
        │
        ▼
   FactChecker :10004
      ├──────────────► Searcher :10002
      └──────────────► Reader   :10003
```

### Why these frameworks?

- **PocketFlow**: explicit branching query decomposition
- **smolagents**: tool-calling loops around search and page extraction
- **LangGraph**: bounded verification loop with repeatable graph structure
- **Pydantic AI**: structured final report output
- **A2A SDK**: HTTP protocol boundary between coordinator and agents
- **Mesop**: lightweight UI for timeline + report rendering

## Quick Start

### 1. Install

```bash
make install
```

### 2. Configure environment

```bash
# macOS/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Edit `.env` and set:

- `LLM_API_KEY`
- `TAVILY_API_KEY` and `BRAVE_API_KEY` (required for web search; Tavily, Brave, and DuckDuckGo run in parallel)

### 3. Start the agent services

In terminal A:

```bash
make serve-all
```

This starts:

- Planner on `http://localhost:10001`
- Searcher on `http://localhost:10002`
- Reader on `http://localhost:10003`
- FactChecker on `http://localhost:10004`
- Synthesizer on `http://localhost:10005`

### 4. Start the UI

In terminal B:

```bash
make mesop
```

Open `http://localhost:32123`.

### 5. Run tests

```bash
make check
make test
```

## Configuration

### LLM

| Variable | Meaning | Default |
|---|---|---|
| `LLM_MODEL` | OpenRouter model id | `openrouter/elephant-alpha` |
| `LLM_BASE_URL` | OpenRouter base URL | `https://openrouter.ai/api/v1` |
| `LLM_API_KEY` | OpenRouter API key | _(required)_ |

### A2A agent service ports

| Variable | Default |
|---|---|
| `PLANNER_PORT` | `10001` |
| `SEARCHER_PORT` | `10002` |
| `READER_PORT` | `10003` |
| `FACT_CHECKER_PORT` | `10004` |
| `SYNTHESIZER_PORT` | `10005` |

### A2A agent service URLs

| Variable | Default |
|---|---|
| `PLANNER_URL` | `http://localhost:10001` |
| `SEARCHER_URL` | `http://localhost:10002` |
| `READER_URL` | `http://localhost:10003` |
| `FACT_CHECKER_URL` | `http://localhost:10004` |
| `SYNTHESIZER_URL` | `http://localhost:10005` |

### Search / workflow

| Variable | Meaning | Default |
|---|---|---|
| `TAVILY_API_KEY` | Tavily API key | _(required)_ |
| `BRAVE_API_KEY` | Brave Search API key ([dashboard](https://api-dashboard.search.brave.com/)) | _(required)_ |
| `SEARCH_MAX_RESULTS` | Per-provider fetch cap before merge | `5` |
| `RESEARCH_MAX_ROUNDS` | FactChecker max loop rounds | `5` |
| `WORKFLOW_TIMEOUT` | Coordinator timeout (seconds) | `180` |
| `LOG_LEVEL` | One threshold for console and `logs/app.log` | `DEBUG` |
| `MESOP_PORT` | UI port | `32123` |

See `.env.example` for the fully annotated version.

## Testing

```bash
make check
make test
```

Test layers:

- executor unit tests
- HTTP contract tests via `httpx.ASGITransport`
- full pipeline integration over in-memory HTTP A2A services
- progress queue tests

No real ports are bound in tests.

## Troubleshooting

### An agent will not start

Run that agent alone:

```bash
make serve-planner
make serve-searcher
make serve-reader
make serve-fact-checker
make serve-synthesizer
```

Then check `GET /.well-known/agent-card.json` for the service URL.

### The coordinator says an agent is unreachable

- confirm the corresponding `*_URL` matches the running service
- confirm `make serve-all` is still running
- confirm the agent port is not already occupied by another process

### Search quality is poor

- set `TAVILY_API_KEY` and `BRAVE_API_KEY` for the paid/indexed providers
- raise `SEARCH_MAX_RESULTS`
- inspect Searcher logs for provider failures or rate limiting

### UI starts but nothing happens on submit

- verify the five agent services are running first
- verify `LLM_API_KEY` is set
- inspect logs from terminal A (`make serve-all`) and terminal B (`make mesop`)

## Running one agent manually

Each agent can run as its own HTTP A2A service:

```bash
uv run python -m a2a_research.agents.pocketflow.planner
uv run python -m a2a_research.agents.smolagents.searcher
uv run python -m a2a_research.agents.smolagents.reader
uv run python -m a2a_research.agents.langgraph.fact_checker
uv run python -m a2a_research.agents.pydantic_ai.synthesizer
```

## More docs

- `docs/architecture.md`
- `docs/development.md`
- `docs/progress-events.md`
