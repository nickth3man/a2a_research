# Agents

Agent implementations using multiple AI frameworks. Each subdirectory contains a complete agent implementation following the A2A protocol.

## Structure

| Directory | Framework | Purpose |
|-----------|-----------|---------|
| `langgraph/` | LangGraph | LangGraph-based agents (fact checker) |
| `pocketflow/` | PocketFlow | PocketFlow-based agents (adversary, clarifier, planner) |
| `pydantic_ai/` | PydanticAI | PydanticAI-based agents (synthesizer) |
| `smolagents/` | SmolAgents | SmolAgents-based agents (reader, searcher) |
| `stubs/` | Stub | Minimal agent stubs for testing and modular development |

## Architecture

This directory demonstrates a polyglot agent architecture where each agent is built with the framework best suited to its task:

- **LangGraph** for stateful graph-based reasoning (fact checker)
- **PocketFlow** for structured flow and branching logic (adversary, clarifier, planner)
- **PydanticAI** for type-safe structured output (synthesizer)
- **SmolAgents** for tool-augmented agents (reader, searcher)
- **Stubs** for lightweight A2A-compatible placeholders

All agents expose an HTTP interface and register via A2A cards, letting the workflow engine treat them uniformly regardless of underlying framework.

## Adding a New Agent

1. Create a new subdirectory with `main.py`, `card.py`, and framework-specific code
2. Implement the A2A card describing inputs, outputs, and endpoints
3. Add a launch target in `src/a2a_research/backend/entrypoints/launcher.py`
