# Agent-to-Agent Communication Protocols for LLM Systems

Agent-to-Agent (A2A) protocols define structured communication patterns between autonomous AI agents. Unlike single-agent systems where one LLM handles all tasks, multi-agent architectures decompose complex workflows into specialized roles.

## Google A2A Specification

Google's proposed A2A specification defines agents as entities that expose capabilities through standardized message schemas. Each agent declares:
- An agent card describing its skills and accepted input types
- A message format based on JSON-RPC-style request/response pairs
- A task lifecycle with states: submitted, working, completed, failed

## Communication Patterns

The three primary patterns are:
1. **Orchestrator-worker**: A central agent dispatches subtasks and aggregates results.
2. **Pipeline**: Agents form a sequential chain where each agent's output feeds the next.
3. **Peer-to-peer**: Agents negotiate directly without a central coordinator.

For research and claim verification tasks, the orchestrator-worker pattern with LangGraph state management provides the best balance of control and flexibility. Each agent operates as a LangGraph node with typed state channels for inter-agent communication.
