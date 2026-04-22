# Searcher

SmolAgents-based web search agent that queries multiple search providers, deduplicates results, and returns ranked hits.

## Agent Role in the Pipeline

The Searcher is the discovery step. It:
- receives one or more search queries
- runs web search across the supported providers
- deduplicates hits by URL
- returns a ranked list of relevant sources for downstream reading and verification

## Framework

- **SmolAgents**
- Uses a `ToolCallingAgent` with a web search tool
- Runs as an A2A HTTP service

## Key Files

| File | Purpose |
| --- | --- |
| `__init__.py` | Public exports for the Searcher package |
| `__main__.py` | Runs the Searcher service with `uvicorn` |
| `agent.py` | Builds the SmolAgents agent and step callback for tool-call telemetry |
| `card.py` | Static A2A agent card for `AgentRole.SEARCHER` |
| `core.py` | Core query execution, result merging, status derivation, and telemetry |
| `main.py` | A2A `AgentExecutor` and HTTP app builder |
| `payload.py` | Request payload extraction and query coercion |
| `prompt.py` | Loads the Searcher prompt |
| `prompt_SEARCHER_PROMPT.txt` | Prompt telling the agent to return JSON hits only |
| `result.py` | Enqueues the search-hits artifact and task status |
| `results.py` | Parses agent output and merges with direct-search fallback |
| `tools.py` | SmolAgents web search tool wrapper around `web_search` |

## Input / Output Contract

### Input
Expected payload keys:
- `queries`: list of strings
- or `query`: single string
- optional `session_id`
- optional `handoff_from`

### Output
Artifact name: `search-hits`

Returned data:
- `queries_used`
- `hits`: list of search hit objects
- `errors`: list of errors encountered
- `providers_successful`: list of providers that returned hits

### Fallback behavior
If the agent returns no usable JSON hits, the implementation can merge in direct `web_search()` fallback results.

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.smolagents.searcher
```

Or use the project service target:

```bash
make serve-searcher
```

The service binds to `settings.searcher_port`.

## Prompt Ownership Notes

- `prompt_SEARCHER_PROMPT.txt` defines the exact JSON output contract
- `prompt.py` only loads the prompt file
- The SmolAgents tool is `web_search(query: str)`
- The prompt requires deduplicated, non-invented URLs and snippets only, not freeform summaries

## Behavior Notes

- The agent callback emits tool-call telemetry for each tool invocation
- Search results are merged and sorted by relevance
- If no providers succeed, the service returns a failed status with the collected errors
- Multiple queries are handled in parallel where possible
