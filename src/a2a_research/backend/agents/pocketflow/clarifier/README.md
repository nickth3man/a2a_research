# Clarifier

PocketFlow-based query disambiguation agent that decides whether a user query is already clear or needs alternate interpretations before research proceeds.

## Agent Role in the Pipeline

The Clarifier is an early pipeline step. It:
- inspects the raw user query
- determines whether the query is unambiguous
- emits candidate interpretations when needed
- commits to a final interpretation
- writes a short audit note explaining the choice

This protects downstream agents from executing on the wrong intent.

## Framework

- **PocketFlow**
- Uses an explicit async flow with disambiguate → commit → audit → terminal
- Runs as an A2A HTTP service

## Key Files

| File | Purpose |
| --- | --- |
| `__init__.py` | Re-exports flow builder, executor, and service helpers |
| `__main__.py` | Runs the Clarifier service with `uvicorn` |
| `card.py` | Static A2A agent card for `AgentRole.CLARIFIER` |
| `events.py` | Artifact/status enqueue helpers for the final result |
| `extract.py` | Request payload and query extraction helpers |
| `flow.py` | PocketFlow wiring and the public `clarify()` function |
| `main.py` | A2A `AgentExecutor` and HTTP app builder |
| `nodes.py` | Node definitions for disambiguation, commit, terminal, and audit export |
| `nodes_audit.py` | Audit note generation node |
| `nodes_commit.py` | Commits the chosen interpretation |
| `nodes_helpers.py` | Ambiguity heuristics and disambiguation normalization helpers |
| `nodes_terminal.py` | Terminal node |
| `prompt.py` | Loads Clarifier prompts from text |
| `prompt_AUDIT_PROMPT.txt` | Prompt for audit-note generation |
| `prompt_DISAMBIGUATE_PROMPT.txt` | Prompt for query disambiguation |

## Input / Output Contract

### Input
Expected payload keys:
- `query`: string
- `query_class`: one of `factual | comparative | temporal | opinion | open_ended`
- optional `session_id`
- optional `handoff_from`

### Output
Artifact name: `clarify`

Returned data:
- `disambiguations`: list of interpretation candidates
- `committed_interpretation`: final query interpretation
- `audit_note`: concise explanation

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.pocketflow.clarifier
```

Or use the project service target:

```bash
make serve-clarifier
```

If the repository's launcher exposes it, the service binds to `settings.clarifier_port`.

## Prompt Ownership Notes

- `prompt_DISAMBIGUATE_PROMPT.txt` defines the JSON contract for disambiguation
- `prompt_AUDIT_PROMPT.txt` defines the audit-note output format
- `prompt.py` only loads those files and does not encode policy itself
- The deterministic heuristic in `nodes_helpers.py` can bypass the LLM for obviously unambiguous factual queries

## Behavior Notes

- If the query is short and not obviously comparative/opinionated, the clarifier may auto-commit without an LLM call
- Invalid or missing LLM output falls back to the original query
- Audit generation is best-effort and degrades gracefully to a generic audit note
