# Adversary

PocketFlow-based adversarial analysis agent that stress-tests claims by evaluating evidence quality, challenging conclusions, and generating inversion queries.

## Agent Role in the Pipeline

The Adversary is the critique / stress-test step. It does not gather evidence itself; instead it:
- evaluates whether supporting evidence is strong, independent, and balanced
- challenges a tentative verdict
- generates counter-search queries that can surface contradictions

This agent helps reduce false confidence before synthesis.

## Framework

- **PocketFlow**
- Built as a small node graph with explicit node chaining
- Runs as an A2A HTTP service in the same backend architecture as the other agents

## Key Files

| File                                | Purpose                                                              |
| ----------------------------------- | -------------------------------------------------------------------- |
| `nodes.py`                            | Backward-compatible node re-export module                            |
| `nodes_challenge.py`                  | Final adversarial challenge node; returns HOLDS/WEAKENED/REFUTED     |
| `nodes_evaluate.py`                   | Evidence quality evaluation node; scores independence, quality, bias |
| `nodes_inversion.py`                  | Generates inversion queries and terminal node                        |
| `prompt.py`                           | Loads the node system prompts                                        |
| `prompt_CHALLENGE_PROMPT.txt`         | Prompt for final challenge decision                                  |
| `prompt_EVALUATE_EVIDENCE_PROMPT.txt` | Prompt for evidence-quality evaluation                               |
| `prompt_INVERSION_QUERY_PROMPT.txt`   | Prompt for generating counter-evidence search queries                |

## Input / Output Contract

### Input
Shared node state expects at least:
- `claim`: a `Claim`
- `tentative_verdict`: tentative claim verification object
- `evidence`: list of evidence units
- `independence_graph`: source relationship graph

### Output
Node outputs:
- `evaluation`: evidence analysis structure
- `challenge_result`: `HOLDS | WEAKENED | REFUTED`
- `confidence_adjustment`: float delta
- `inversion_queries`: list of exactly 3 query strings when generated
- `error`: optional error string

## How to Run Standalone

Run the HTTP service:

```bash
python -m a2a_research.agents.pocketflow.adversary
```

If no module entrypoint is exposed elsewhere in the repo, the package is primarily intended to be launched through the agent service launcher. Check the top-level service targets for the exact command used in this repository.

## Prompt Ownership Notes

- The prompt files are the source of truth
- `prompt.py` only loads text from disk
- Each node owns its own prompt usage:
  - `nodes_evaluate.py` → `EVALUATE_EVIDENCE_PROMPT`
  - `nodes_challenge.py` → `CHALLENGE_PROMPT`
  - `nodes_inversion.py` → `INVERSION_QUERY_PROMPT`
- All prompts require JSON-only output and the nodes include fallback logic if the LLM fails

## Behavior Notes

- `nodes_evaluate.py` computes a fallback neutral evaluation if the LLM is unavailable
- `nodes_challenge.py` and `nodes_inversion.py` also have deterministic fallbacks
- The design favors safe degradation over hard failure when the LLM response is malformed
