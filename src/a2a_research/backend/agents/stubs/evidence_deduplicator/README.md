# Evidence Deduplicator Stub

Minimal A2A-compatible stub for the evidence deduplication agent.

## Why this exists

This stub gives the backend a lightweight stand-in for the real evidence deduplicator so the rest of the system can be developed and tested without the full production implementation. It simulates the shape of the agent, the request flow, and the normalization result.

## What it mimics

- An A2A agent service exposed over HTTP
- A card advertising an `EvidenceDeduplicator` agent
- A normalization step that turns page content into evidence records
- Deduplication against already-known evidence IDs

## Input contract

The executor reads the first JSON-like payload from the incoming A2A message.

Expected fields:

- `pages`: list of page dicts
- `existing_evidence`: list of already-known evidence dicts
- `session_id`: optional session identifier used for progress reporting

Each page dict is expected to contain at least:

- `url`
- `markdown`
- `title` (optional)

## Output contract

The agent emits a completed task with one artifact named `normalize` containing:

- `new_evidence`: normalized evidence records not present in `existing_evidence`
- `dedupe_stats`: basic counts for input pages and new evidence
- `independence_graph`: empty placeholders for claim/publisher and citation relationships

Each generated evidence item includes stable IDs, source metadata, content hash, quoted passage data, and credibility placeholders.

## Key files

| File | Purpose |
|------|---------|
| `card.py` | Declares the A2A card, service URL, and `normalize` skill |
| `main.py` | Implements the stub executor and HTTP app wiring |
| `normalize.py` | Converts page dicts into normalized evidence items |
| `payload.py` | Extracts the request payload from A2A message parts |
| `__init__.py` | Re-exports the public stub entry points |

## Behavior notes

- Evidence IDs are derived from URL + content hash prefix.
- Existing evidence IDs are used to suppress duplicates.
- The stub does not perform real source ranking or deep independence analysis.
- Progress events are emitted to mirror the production agent lifecycle.
