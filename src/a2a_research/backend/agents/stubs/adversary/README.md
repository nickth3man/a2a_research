# Adversary Stub

Minimal A2A-compatible stand-in for the full PocketFlow adversary agent.

## Why this exists

This stub lets the backend exercise adversary routing, task handling, progress events, and artifact emission without loading the real agent implementation or any model-backed logic.

It mimics the production adversary at the HTTP/A2A boundary, but its behavior is intentionally simple and deterministic.

## What it mimics

- The adversary agent card and service URL
- A request/response loop over A2A tasks
- Progress updates for start/completion
- A final artifact shaped like the real adversary output

## Input contract

`AdversaryExecutor.execute()` reads the request payload from the task message.

Expected fields:

- `claims` — list of claim objects; only dict items are processed
- `session_id` — optional session identifier used for progress emission

Payloads may arrive as structured data parts or JSON text parts.

## Output contract

The stub always treats each claim as **HOLDS** and returns a deterministic artifact with:

```json
{
  "challenge_results": [
    {
      "claim_id": "...",
      "challenge_result": "HOLDS",
      "counter_evidence_queries": [],
      "counter_evidence_refs": []
    }
  ],
  "counter_evidence_queries": [],
  "counter_evidence_refs": []
}
```

It also emits `STEP_STARTED` / `STEP_COMPLETED` progress events for the adversary role.

## Key files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `AdversaryExecutor` and `build_http_app` |
| `card.py` | Defines the A2A agent card (`Adversary`, port `10010`) |
| `main.py` | Implements the stub executor, payload parsing, artifact emission, and HTTP app builder |

## Notes

- `main.py` contains a passthrough implementation: every claim is accepted.
- `build_http_app()` wires the stub into the standard A2A Starlette app.
- This directory should stay lightweight and deterministic for tests and local development.
