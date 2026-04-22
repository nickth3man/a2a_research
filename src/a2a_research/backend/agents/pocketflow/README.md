# PocketFlow Agents

PocketFlow-based agent implementations. PocketFlow is a good fit for agents that follow a structured sequence of steps or a branching flow with reusable nodes.

## What lives here

This directory contains the PocketFlow-powered agents used by the backend:
- `adversary/`
- `clarifier/`
- `planner/`

## Structure

| Directory | Purpose |
| --------- | ------- |
| `adversary/` | Agent that stress-tests claims and evidence |
| `clarifier/` | Agent that disambiguates user intent |
| `planner/` | Agent that breaks a request into research steps |

## When to use PocketFlow

Use PocketFlow when the agent needs:
- a predictable pipeline of steps
- reusable node composition
- clear branching or routing logic
- testable flow-based orchestration

PocketFlow is especially useful for decomposition-style agents such as clarification, planning, and adversarial review.

## Common patterns

PocketFlow agents usually organize code around flow components:
- `nodes.py` defines reusable steps in the pipeline
- flow or composition modules wire nodes together
- agent-specific state and events move through the flow
- the final result is produced after the flow completes

Prefer keeping domain-specific reasoning in the leaf agent directory instead of expanding this README with implementation details.

## Files

| File | Purpose |
| ---- | ------- |
| `__init__.py` | Package initialization |

## Agents

### Adversary
Challenges claims and evidence to find weak points in reasoning. This agent is useful when you want a deliberate critique or stress test of conclusions.

### Clarifier
Analyzes user input for ambiguity and produces a disambiguated interpretation. Use this agent when the request needs refinement before downstream processing.

### Planner
Classifies a request and produces a structured research plan with sub-questions and search targets. Use this agent when the workflow needs decomposition before search or synthesis.

All three agents use PocketFlow's node-based composition model.
