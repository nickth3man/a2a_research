# Critic Stub

Minimal A2A-compatible stand-in for the critic agent.

## Why it exists

This stub lets the workflow exercise a critic step without running a real model-backed review service. It is used for local development, protocol testing, and end-to-end workflow checks where the critic role must exist but should always be cheap and deterministic.

## What it mimics

It mimics the critic agent service shape:

- A published A2A agent card
- An HTTP app built from the A2A request handler stack
- A task executor that emits progress, an artifact, and a completed status

Unlike a real critic, it always passes.

## Input contract

`main.py` extracts the request payload from the incoming A2A message body.

Accepted input shape:

- Any A2A message whose parts contain a JSON object or text that parses as JSON
- `session_id` is read from the payload if present
- Other fields are ignored by the stub

Behavior:

- If no payload is present, it falls back to `{}`
- If the payload cannot be parsed, it is ignored
- The executor does not perform real critique logic

## Output contract

The executor always returns a passing critique artifact with this shape:

```json
{
  "passed": true,
  "critique": "No issues found (stub).",
  "suggested_improvements": [],
  "iteration_count": 0,
  "warnings": []
}
```

It also:

- emits `critic_started` and `critic_completed` progress events
- publishes an `Artifact` named `critique`
- marks the task as completed

## Key files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `CriticExecutor` and `build_http_app` |
| `card.py` | Defines `CRITIC_CARD` and the `critique` skill |
| `main.py` | Implements the stub executor, payload parsing, artifact emission, and HTTP app builder |

## Notes

- Service card URL: `http://localhost:10011`
- Skill ID: `critique`
- This stub is intentionally deterministic and side-effect free beyond task/progress events
