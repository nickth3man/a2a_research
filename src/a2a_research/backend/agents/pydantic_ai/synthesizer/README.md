# Synthesizer

PydanticAI-based report writer that converts verified claims and source evidence into a final structured research report.

## Agent Role in the Pipeline

The Synthesizer is the final pipeline step. It:
- receives the user query
- consumes verified claims from upstream agents
- consumes deduplicated source data
- writes a coherent, citation-grounded `ReportOutput`

This is the user-facing synthesis stage.

## Framework

- **PydanticAI**
- Uses a typed `Agent` with schema-constrained output
- Runs as an A2A HTTP service

## Key Files

| File | Purpose |
| --- | --- |
| `__init__.py` | Public exports for the synthesizer package |
| `__main__.py` | Runs the Synthesizer service with `uvicorn` |
| `agent.py` | Builds the PydanticAI model and cached agent |
| `artifacts.py` | Enqueues structured and markdown report artifacts |
| `card.py` | Static A2A agent card for `AgentRole.SYNTHESIZER` |
| `core.py` | Prompt construction, agent invocation, and output sanitization |
| `main.py` | A2A `AgentExecutor` and HTTP app builder |
| `payload.py` | Request payload extraction and coercion helpers |
| `prompt.py` | Loads the synthesizer prompt |
| `prompt_SYNTHESIZER_PROMPT.txt` | Prompt defining report-writing rules |

## Input / Output Contract

### Input
Expected payload keys:
- `query`: string
- `verified_claims` or `claims`: list of verified claim objects or dicts
- `sources`: list of source objects or dicts
- optional `session_id`
- optional `handoff_from`

### Output
The service enqueues two artifacts:
- `report` — JSON data artifact containing the `ReportOutput`
- `report-markdown` — markdown rendering of the report

`ReportOutput` is schema-validated by PydanticAI and sanitized before emission.

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.pydantic_ai.synthesizer
```

Or use the project service target:

```bash
make serve-synthesizer
```

The service binds to `settings.synthesizer_port`.

## Prompt Ownership Notes

- The report-writing policy lives in `prompt_SYNTHESIZER_PROMPT.txt`
- `prompt.py` just loads the file
- The prompt is the source of truth for citation behavior, tone, and output expectations
- The agent enforces `ReportOutput` as the final output type and retries schema generation when needed

## Behavior Notes

- The synthesizer expects citations to come only from supplied sources or claim sources
- Invalid or missing structured output is retried by PydanticAI
- Both JSON and markdown artifacts are emitted for downstream consumers
