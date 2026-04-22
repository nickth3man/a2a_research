# Agent Stubs

Minimal A2A-compatible agent implementations used for testing, development, and placeholder services.

## What lives here

This directory contains stub versions of agent roles used elsewhere in the backend:
- `adversary/`
- `clarifier/`
- `critic/`
- `evidence_deduplicator/`
- `postprocessor/`
- `preprocessor/`
- `ranker/`

## When to use stubs

Use stubs when you need:
- fast local development without full framework startup
- integration tests that should avoid LLM calls
- protocol and orchestration validation
- temporary placeholders for unfinished agents

Stub agents are designed to behave like their full counterparts at the HTTP/A2A interface level while keeping implementation minimal.

## Common patterns

Stub agents typically keep the same basic shape as full agents:
- `card.py` defines the A2A card
- `main.py` exposes the HTTP service and endpoints
- optional helper modules hold stub-specific payload handling

This lets workflow code interact with stubs exactly like it would with production agents.

## Files

| File | Purpose |
| ---- | ------- |
| `__init__.py` | Package initialization |

## Purpose

Each stub represents a minimal version of an agent role so the system can be developed and tested without depending on framework-specific logic or external model calls.

The `evidence_deduplicator/` stub also includes `normalize.py` and `payload.py` for deduplication-specific data structures.
