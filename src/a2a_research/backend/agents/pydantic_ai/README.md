# PydanticAI Agents

PydanticAI-based agent implementations. PydanticAI is a good fit for agents that need typed, schema-constrained outputs and reliable structured responses.

## What lives here

This directory contains the PydanticAI-powered agents used by the backend:
- `synthesizer/`

## Structure

| Directory | Purpose |
| --------- | ------- |
| `synthesizer/` | Final synthesis agent that turns upstream evidence into a report |

## When to use PydanticAI

Use PydanticAI when the agent needs:
- strict output schemas
- validated structured results
- strongly typed intermediate and final payloads
- reliable downstream consumption by other services

PydanticAI is especially useful for synthesis or reporting steps where output format matters as much as content.

## Common patterns

PydanticAI agents commonly center around:
- `agent.py` for agent configuration and execution
- Pydantic models for input, output, and validation
- prompt and tool definitions near the agent entry point
- structured response objects rather than free-form text

Keep the report-specific schema and formatting details in the leaf directory, not in this framework README.

## Files

| File | Purpose |
| ---- | ------- |
| `__init__.py` | Package initialization |

## Synthesizer Agent

The synthesizer collects verified claims and evidence from upstream agents, formats them according to a Pydantic schema, and produces a final research report with citations.

This framework is the right choice when the consumer needs dependable, machine-readable output.
