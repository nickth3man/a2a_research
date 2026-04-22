# Fact Checker

LangGraph-based verification agent that checks atomic claims against gathered web evidence and returns a structured verdict set.

## Agent Role in the Pipeline

The Fact Checker is the verification step in the 5-agent research pipeline. It receives:
- the original user query
- atomic claims from the Planner
- fetched web evidence from upstream search/reader steps
- source metadata

It then verifies each claim against the evidence and emits a final artifact containing updated claim verdicts and any verification errors.

## Framework

- **LangGraph**
- Service entrypoint is an **A2A HTTP agent**
- Uses the shared backend LLM provider and progress/event plumbing

## Key Files

| File                     | Purpose                                                                            |
| ------------------------ | ---------------------------------------------------------------------------------- |
| `__init__.py`              | Re-exports `FactCheckState`, `FactCheckerExecutor`, and `run_fact_check`                 |
| `__main__.py`              | Runs the service with `uvicorn` using the FactChecker port                           |
| `card.py`                  | Builds the static A2A agent card for `AgentRole.FACT_CHECKER`                        |
| `core.py`                  | Main verification orchestration and short-circuit behavior when no evidence exists |
| `main.py`                  | A2A `AgentExecutor` implementation and HTTP app builder                              |
| `node_support.py`          | Shared prompt-building and parsing helpers for LangGraph verification nodes        |
| `nodes.py`                 | Node export shim for `verify_claims`                                                 |
| `payload.py`               | Request payload extraction and coercion helpers                                    |
| `prompt.py`                | Loads the verifier system prompt from text                                         |
| `prompt_VERIFY_PROMPT.txt` | Prompt instructing the model to return JSON verdicts only                          |
| `result.py`                | Enqueues the verified result artifact and task status                              |
| `state.py`                 | TypedDict state and run-result schema used by LangGraph                            |
| `verify_route.py`          | Core claim verification logic and LLM call path                                    |

## Input / Output Contract

### Input
Expected payload keys:
- `query`: string
- `claims`: list of claim objects or dicts
- `evidence`: list of page content objects or dicts
- `sources`: list of source objects or dicts
- optional `session_id`
- optional `handoff_from`

### Output
The task artifact is `verified`, containing:
- `verified_claims`
- `sources`
- `errors`
- `search_exhausted`
- `rounds`

### Claim verification output shape
Each claim is returned with:
- `id`
- `text`
- `verdict`
- `confidence`
- `sources`
- `evidence_snippets`

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.langgraph.fact_checker
```

Or use the project service target:

```bash
make serve-fact-checker
```

The service binds to `settings.fact_checker_port`.

## Prompt Ownership Notes

- The verifier prompt lives in `prompt_VERIFY_PROMPT.txt`
- `prompt.py` only loads the text file; the text file is the source of truth
- `verify_route.py` also builds a runtime user prompt with claim/evidence context
- The prompt requires JSON-only output and the parser falls back safely if the model output is invalid

## Behavior Notes

- If no evidence is provided, the agent short-circuits and marks claims as `INSUFFICIENT_EVIDENCE`
- If the LLM fails or returns invalid JSON, parsing falls back to the original claims
- The service emits progress, prompt, response, and claim-verdict events for observability
