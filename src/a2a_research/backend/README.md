# Backend

Main backend package for the A2A research pipeline. Contains agent implementations, core infrastructure, workflow orchestration, LLM integrations, and external tool bindings.

## Structure

| Directory | Purpose |
|-----------|---------|
| `agents/` | Agent implementations across multiple frameworks |
| `core/` | Shared models, settings, utilities, and protocol code |
| `entrypoints/` | Application entry points and service launcher |
| `llm/` | LLM provider configuration and integration |
| `tools/` | External tool integrations (search, fetch) |
| `workflow/` | Workflow engine and orchestration logic |

## Architecture

The backend follows a layered architecture:

- **Agents layer** - Individual agent services implemented with different frameworks (PocketFlow, LangGraph, Pydantic AI, smolagents) plus lightweight stubs for testing
- **Core layer** - Shared Pydantic models, A2A protocol implementation, configuration, logging, and progress tracking
- **Workflow layer** - Central orchestration engine that coordinates agents through the research pipeline
- **Tools layer** - Abstracted search and fetch utilities with multiple provider support
- **LLM layer** - Unified LLM provider configuration used across agents

Each agent runs as an independent HTTP service and communicates via the A2A protocol, allowing the workflow engine to mix and match implementations.
