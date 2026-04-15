# PocketFlow State Management for Multi-Agent Workflows

PocketFlow is a minimal Python framework for building flow-based applications. It uses nodes and flows with a shared store for state management, making it ideal for multi-agent pipelines where each step needs access to accumulated context.

## Core Concepts

**Node**: The atomic unit of work. Each node has `prep()` (read from shared store), `exec()` (compute), and `post()` (write back to shared store) phases. PocketFlow provides `Node`, `AsyncNode`, `BatchNode`, and `AsyncBatchNode` variants.

**Flow**: Orchestrates nodes into a directed graph. Use `>>` for sequential transitions and `-` for conditional branching based on action strings returned by nodes.

**Shared Store**: A global dictionary that all nodes read from and write to. This is the primary state mechanism in PocketFlow — simple, explicit, and easy to inspect.

## Pattern: Pipeline with Shared State

For research tasks, a natural PocketFlow pattern is:

1. **Researcher node** retrieves relevant documents and writes them to the shared store
2. **Analyst node** reads the documents, decomposes claims, and writes atomic claims back
3. **Verifier node** reads the claims and evidence, assigns verdicts, and updates the store
4. **Presenter node** reads all verified claims and renders the final report

This maps directly to the 4-agent research system using sequential `AsyncNode` wrappers connected with `>>`.

## Integration with Local A2A Contracts

Each agent in the pipeline exposes an A2A-shaped contract: a typed input schema, output schema, and agent card. Even though all agents run in-process within a single PocketFlow invocation, maintaining A2A contracts ensures clean interfaces and future extensibility to distributed deployment.
