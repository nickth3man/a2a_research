# Architecture

## System shape

The system is split into a coordinator process and five HTTP A2A agent services.

- the **Mesop UI** calls `run_research_async()`
- the **coordinator** sends A2A HTTP messages to agent URLs
- the **FactChecker** is itself an agent and also calls peer agents over HTTP
- a local in-process **ProgressQueue/Bus** is used only for UI progress updates inside the coordinator process

## Agent responsibilities

### Planner (PocketFlow)

- classifies the query into a decomposition strategy
- branches through PocketFlow nodes
- returns `claims` and `seed_queries`

### Searcher (smolagents)

- runs tool-calling loops over `web_search()`
- can refine weak queries across multiple steps
- returns `hits`, `errors`, and `providers_successful`

### Reader (smolagents)

- runs tool-calling loops over `fetch_and_extract()`
- uses the current claim context to prioritize URLs
- returns extracted `pages`

### FactChecker (LangGraph)

- loops over Searcher → Reader → Verify
- stops when claims converge or search is exhausted
- returns `verified_claims`, `sources`, `errors`, `rounds`

### Synthesizer (Pydantic AI)

- turns verified claims and sources into structured `ReportOutput`
- renders markdown from that structured result

## Message flow

1. UI submits query
2. Coordinator calls Planner
3. Coordinator calls FactChecker
4. FactChecker calls Searcher and Reader over HTTP as needed
5. Coordinator calls Synthesizer
6. UI renders final report + timeline + sources

## A2A boundaries

- cards are advertised by each service at its HTTP endpoint
- the client resolves role → URL from config
- tests use `httpx.ASGITransport` to keep everything in-memory

## Failure model

- provider failures should be surfaced in task status messages
- connection failures should become clear “agent not reachable” coordinator errors
- Searcher degrades to DDGS-only mode when Tavily is disabled
