# LangGraph Agents

LangGraph-based agent implementations. LangGraph is a good fit for agents that need explicit state transitions, multi-step reasoning, and conditional branching.

## What lives here

This directory contains the LangGraph-powered agents used by the backend. At present, that is the `fact_checker/` agent.

## Structure

| Directory | Purpose |
| --------- | ------- |
| `fact_checker/` | Fact-checking agent with verification-oriented graph nodes |

## When to use LangGraph

Use LangGraph when the agent needs:
- a clear state machine or graph of steps
- branching logic based on intermediate results
- repeated verification or multi-stage decision-making
- state shared across multiple passes of reasoning

LangGraph works well for fact-checking and other tasks where the order of operations matters and the agent may need to take different paths depending on evidence quality.

## Common patterns

LangGraph agents typically separate logic into graph nodes and edges:
- `nodes.py` or equivalent modules define the individual reasoning or tool-use steps
- a graph assembly module connects nodes into a stateful workflow
- agent-specific state models define what flows through the graph
- the final node returns a structured verdict or output payload

Keep detailed verification logic inside the leaf agent directory. This README should stay framework-level and describe the shared LangGraph conventions only.

## Files

| File | Purpose |
| ---- | ------- |
| `__init__.py` | Package initialization |

## Fact Checker Agent

The fact checker accepts a claim and supporting evidence, routes the input through verification steps, evaluates source credibility and evidence strength, and returns a structured verdict with reasoning.

The graph-based design is useful when different claims need different verification paths, such as factual claims versus statistical claims.
