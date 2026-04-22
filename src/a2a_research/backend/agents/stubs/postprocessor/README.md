# Postprocessor Stub

Lightweight A2A-compatible stand-in for the post-processing agent.

## Why this exists

This stub lets the backend run, test, and orchestrate a postprocessor service without loading a full agent implementation. It is useful for:

- local development
- protocol / service integration tests
- placeholder wiring while the real postprocessor is unavailable

## What it mimics

It mimics a post-processing agent that:

- formats a research report into markdown
- preserves a JSON representation of the report
- advertises citation rendering, PII redaction, and output formatting skills

The stub exposes the same A2A-style HTTP shape as a real agent, including an agent card and task execution lifecycle.

## Input contract

The executor reads the incoming A2A message payload and expects a dictionary-like body. Relevant fields are:

- `report` — the report object to format
- `session_id` — optional session identifier used for progress emission

If `report` is a mapping, the stub expects common fields such as:

- `title`
- `summary`
- `sections` with `heading` and `body`

If the payload is missing or not JSON-like, the stub falls back to empty data or string coercion.

## Output contract

The executor returns one artifact named `postprocess` containing `formatted_outputs` with:

- `markdown` — rendered markdown report
- `json` — JSON string when the report is a dict, otherwise stringified input

It also emits task status / artifact updates through the A2A event queue and marks the task complete.

## Key files

| File | Purpose |
|------|---------|
| `card.py` | Defines the postprocessor agent card and advertised skill metadata |
| `main.py` | Implements the stub executor, payload extraction, formatting, and HTTP app builder |
| `__init__.py` | Re-exports the executor and app builder for package imports |

## Notes

- HTTP service URL advertised by the card: `http://localhost:10012`
- The current implementation is intentionally minimal and passthrough-oriented
- The stub formats sectioned reports into markdown headings and body text
