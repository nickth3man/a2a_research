# Clarifier Stub

Lightweight stand-in for the real clarifier agent.

## Why this exists

This stub lets the workflow run the clarification stage without starting the full PocketFlow implementation. It is useful for local development, protocol checks, and tests that only need a valid A2A service.

## What it mimics

It mimics the clarifier agent at the HTTP/A2A boundary:

- publishes a clarifier A2A card
- accepts request payloads in the same shape as the real agent
- emits task completion + artifact updates
- reports clarification progress events

## Input / output contract

### Input

- `query`: the user query to clarify
- `session_id`: optional session identifier used for progress tracking

The executor reads the payload from the incoming message parts as either structured data or JSON text.

### Output

The stub always commits to the input query as-is and returns a single `clarify` artifact with:

- `disambiguations: []`
- `committed_interpretation: <original query>`
- `audit_note: "No disambiguation needed (stub)."`

It then marks the task completed.

## Key files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports the public stub API |
| `card.py` | Defines the clarifier A2A card and skill metadata |
| `main.py` | Implements the stub executor and HTTP app |
| `README.md` | This documentation |

## Notes

- `main.py` defines `ClarifierExecutor`
- `build_http_app()` wires the executor to an in-memory task store and the clarifier card
- `card.py` advertises the service at `http://localhost:10007`
