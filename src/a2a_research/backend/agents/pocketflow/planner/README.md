# Planner

PocketFlow-based planning agent that decomposes the user query into atomic claims and seed queries for downstream search and verification.

## Agent Role in the Pipeline

The Planner is the first structured reasoning step in the 5-agent pipeline. It:
- classifies the query as factual, comparative, temporal, or fallback
- decomposes the query into atomic claims
- generates seed search queries
- optionally builds a claim DAG for downstream orchestration

Its output is the handoff shape consumed by the Searcher and Fact Checker.

## Framework

- **PocketFlow**
- Async flow with branch-specific decomposition nodes
- Uses the shared OpenRouter-backed LLM infrastructure

## Key Files

| File | Purpose |
| --- | --- |
| `__init__.py` | Public exports for the planner package |
| `__main__.py` | Runs the Planner service with `uvicorn` |
| `card.py` | Static A2A agent card for `AgentRole.PLANNER` |
| `events.py` | Plan artifact and status enqueue helper |
| `extract.py` | Request payload and query extraction helpers |
| `flow.py` | PocketFlow wiring and public `plan()` API |
| `main.py` | A2A `AgentExecutor` and HTTP app builder |
| `nodes.py` | Classification, decomposition, seed, fallback, and terminal nodes |
| `nodes_base.py` | Shared decomposition base node and prompt/LLM plumbing |
| `nodes_extract.py` | Extraction helpers, freshness inference, and DAG builder |
| `prompt.py` | Loads all planner prompt text files |
| `prompt_CLASSIFIER_PROMPT.txt` | Prompt for query strategy classification |
| `prompt_FACTUAL_PROMPT.txt` | Prompt for factual decomposition |
| `prompt_COMPARATIVE_PROMPT.txt` | Prompt for comparative decomposition |
| `prompt_TEMPORAL_PROMPT.txt` | Prompt for temporal decomposition |

## Input / Output Contract

### Input
Expected payload keys:
- `query`: string
- optional `session_id`
- optional `handoff_from`

### Output
Artifact name: `plan`

Returned data:
- `query`
- `claims`: list of atomic claims
- `claim_dag`: DAG structure describing claim refinement
- `seed_queries`: list of search queries

### Fallback behavior
If decomposition fails, the planner emits a fallback plan with a single claim based on the original query.

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.pocketflow.planner
```

Or use the project service target:

```bash
make serve-planner
```

The service binds to `settings.planner_port`.

## Prompt Ownership Notes

- `prompt_CLASSIFIER_PROMPT.txt` chooses the decomposition strategy
- `prompt_FACTUAL_PROMPT.txt`, `prompt_COMPARATIVE_PROMPT.txt`, and `prompt_TEMPORAL_PROMPT.txt` define the branch prompts
- `prompt.py` only loads prompt text from disk
- `nodes_base.py` owns the runtime prompt emission and shared parsing logic
- `nodes_extract.py` owns structural extraction and freshness heuristics

## Behavior Notes

- The classifier uses a heuristic fallback when the LLM request fails
- Decomposition nodes are specialized by query type
- Seed queries default to the first few claim texts if the model does not provide them
- A default claim DAG is synthesized when needed so downstream systems always receive a usable structure
