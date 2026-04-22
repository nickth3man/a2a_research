# SmolAgents

SmolAgents-based agent implementations. SmolAgents is a good fit for lightweight agents that use tools dynamically during reasoning, especially for search and retrieval tasks.

## What lives here

This directory contains the SmolAgents-powered agents used by the backend:
- `reader/`
- `searcher/`

## Structure

| Directory | Purpose |
| --------- | ------- |
| `reader/` | Agent that fetches and extracts content from web sources |
| `searcher/` | Agent that finds relevant sources for a query |

## When to use SmolAgents

Use SmolAgents when the agent needs:
- tool-augmented reasoning
- dynamic tool selection
- lightweight agent setup
- search and fetch behavior during execution

SmolAgents is especially useful for retrieval-oriented tasks where the agent needs to choose the right external tool at runtime.

## Common patterns

SmolAgents agents usually follow a compact structure:
- `agent.py` or equivalent defines the agent and tool bindings
- tools are registered directly with the agent
- the agent invokes search/fetch tools as needed during reasoning
- outputs are usually evidence snippets, source lists, or extracted content

Keep provider-specific search details and parsing logic in the leaf agent directories.

## Files

| File | Purpose |
| ---- | ------- |
| `__init__.py` | Package initialization |

## Agents

### Searcher
Finds relevant sources for research sub-questions. It can use multiple search providers to return ranked results.

### Reader
Fetches and structures content from web sources. It extracts evidence snippets and preserves citation metadata.

Both agents rely on SmolAgents' tool-driven workflow to perform retrieval tasks.
