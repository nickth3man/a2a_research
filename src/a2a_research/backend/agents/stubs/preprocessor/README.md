# Preprocessor Stub

Minimal A2A-compatible stand-in for the preprocessor agent.

## Why this exists

This stub gives the research pipeline a lightweight preprocessor service without requiring the full production implementation. It is useful for local development, protocol checks, and tests that need the agent boundary to exist but do not need real model-backed preprocessing.

## What it mimics

The stub mimics a real preprocessor agent at the HTTP/A2A interface level:

- advertises an A2A card at `http://localhost:10006`
- accepts task requests through the standard A2A request handler
- emits a completed task with a single `preprocess` artifact
- reports progress events for start and completion

Behavior-wise, it performs only simple heuristics:

- classifies queries as `sensitive`, `subjective`, `unanswerable`, or `factual`
- echoes the incoming query as `sanitized_query`
- flags basic PII-like terms such as password, SSN, and credit card references
- returns empty `domain_hints` in all cases

## Input contract

The executor reads the first message part it can parse as JSON.

Accepted payload shape:

```json
{
  "query": "string",
  "session_id": "string"
}
```

Notes:

- `query` is treated as optional text and defaults to `""`.
- `session_id` is used only for progress emission.
- If the message contains a JSON text part or structured data part, the stub extracts that dictionary.

## Output contract

The stub returns one artifact named `preprocess` containing:

```json
{
  "sanitized_query": "string",
  "query_class": "sensitive | subjective | unanswerable | factual",
  "query_class_confidence": 0.0,
  "pii_findings": [],
  "domain_hints": []
}
```

It then marks the task completed.

## Key files

| File | Purpose |
| --- | --- |
| `__init__.py` | Re-exports the stub executor and HTTP app builder |
| `card.py` | Defines the A2A card metadata and `preprocess` skill |
| `main.py` | Implements the executor, payload parsing, artifact creation, and HTTP app |

## Implementation notes

- Uses `InMemoryTaskStore` for a minimal service runtime.
- Uses the shared A2A compatibility layer to build the HTTP app.
- `cancel()` is a no-op.
