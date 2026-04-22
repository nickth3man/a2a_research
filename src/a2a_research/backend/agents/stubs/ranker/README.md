# Ranker Stub

Minimal A2A-compatible stand-in for the ranker agent.

## Why it exists

This stub lets the workflow exercise ranking coordination without a real ranking model or scoring logic. It keeps the HTTP/A2A surface stable for local development and tests.

## What it mimics

- an agent named `Ranker`
- an A2A card advertised at `http://localhost:10008`
- a rank-style service that accepts hits and returns ranked results

## Input contract

The executor reads the incoming task payload from the request message and expects:

- `hits`: a list of hits
  - each hit may be a dict with a `url` field, or a plain string URL
- `session_id`: optional string used for progress emission

## Output contract

The stub emits one completed artifact named `rank` with this shape:

```json
{
  "ranked_urls": ["..."],
  "credibility_scores": {},
  "freshness_scores": {},
  "selection_rationale": "Passthrough ranking (stub)."
}
```

Behavior is passthrough: it preserves input order, extracts URLs, and does not compute real scores.

## Key files

| File | Purpose |
| --- | --- |
| `__init__.py` | Re-exports `RankerExecutor` and `build_http_app` |
| `card.py` | Defines the A2A card, skills, and service URL |
| `main.py` | Implements the stub executor, payload parsing, and HTTP app |

## Notes

- `main.py` emits progress events for start/completion.
- The executor marks the task completed after writing the artifact.
- `cancel()` is a no-op.
