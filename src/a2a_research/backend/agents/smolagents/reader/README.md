# Reader

SmolAgents-based document reader that fetches URLs and extracts main-page content into structured evidence pages.

## Agent Role in the Pipeline

The Reader is the content acquisition step. It:
- receives one or more URLs
- fetches and extracts page content
- emits page-level evidence artifacts for downstream planning, verification, and synthesis

This agent converts raw URLs into machine-readable page content.

## Framework

- **SmolAgents**
- Uses a `ToolCallingAgent` with a custom fetch tool
- Runs as an A2A HTTP service

## Key Files

| File | Purpose |
| --- | --- |
| `__init__.py` | Public exports for the Reader package |
| `__main__.py` | Runs the Reader service with `uvicorn` |
| `agent.py` | Builds the SmolAgents agent and model |
| `card.py` | Static A2A agent card for `AgentRole.READER` |
| `core.py` | Core `read_urls()` function and fallback extraction behavior |
| `events.py` | Page progress logging and result artifact enqueue helper |
| `main.py` | A2A `AgentExecutor` and HTTP app builder |
| `payload.py` | Request payload extraction and URL list coercion |
| `prompt.py` | Loads the Reader prompt |
| `prompt_READER_PROMPT.txt` | Prompt telling the agent to return page JSON only |
| `tools.py` | SmolAgents tool wrapper around `fetch_and_extract` |

## Input / Output Contract

### Input
Expected payload keys:
- `urls`: list of URLs, or `url` as a single string
- optional `max_chars`
- optional `session_id`
- optional `handoff_from`

### Output
Artifact name: `extracted-pages`

Returned data:
- `pages`: list of page objects with:
  - `url`
  - `title`
  - `markdown`
  - `word_count`

### Fallback behavior
If the SmolAgents path does not return valid JSON pages, the code falls back to direct `fetch_many()` extraction.

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.smolagents.reader
```

Or use the project service target:

```bash
make serve-reader
```

The service binds to `settings.reader_port`.

## Prompt Ownership Notes

- `prompt_READER_PROMPT.txt` defines the exact output contract
- `prompt.py` only loads the prompt file
- The custom tool is `fetch_and_extract(url)`
- The prompt instructs the agent not to paraphrase or truncate the markdown beyond what the tool returns

## Behavior Notes

- Page progress events are emitted per fetched page
- Valid JSON output from the agent is preferred
- The direct extraction fallback keeps the service robust if the LLM/tool loop fails
