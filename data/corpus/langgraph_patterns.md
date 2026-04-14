# LangGraph State Management for Multi-Agent Workflows

LangGraph is a framework for building stateful multi-step LLM applications as directed graphs. It extends LangChain with persistent state management, cycle support, and human-in-the-loop patterns.

## Core Concepts

**StateGraph**: The primary abstraction. Nodes are functions that receive and return a typed state dictionary. Edges define transitions, including conditional routing based on state values.

**State Channels**: Typed keys in the state schema. Channels can use reducers (e.g., `operator.add` for list accumulation) to define how parallel node outputs merge.

**Checkpointers**: Pluggable persistence backends that save graph state after each step. This enables pause/resume, time-travel debugging, and crash recovery.

## Pattern: Orchestrator-Worker with Fan-out

For research tasks, a common pattern is:

1. **Router node** analyzes the query and decides which specialist agents to invoke
2. **Fan-out** sends the query to multiple specialist nodes in parallel
3. **Aggregator node** collects and synthesizes specialist outputs
4. **Reviewer node** evaluates the synthesis for completeness and accuracy

This maps naturally to the 4-agent research system: Researcher (retrieval), Analyst (decomposition), Verifier (fact-checking), and Presenter (synthesis).

## Integration with Local A2A Contracts

Each agent in the graph can expose an A2A-shaped contract: a typed input schema, output schema, and agent card. Even though all agents run in-process within a single LangGraph invocation, maintaining A2A contracts ensures clean interfaces and future extensibility to distributed deployment.
