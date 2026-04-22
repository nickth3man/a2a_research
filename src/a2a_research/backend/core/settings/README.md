# Settings

Typed application settings loaded from `.env` and environment variables. All configuration is validated through Pydantic `BaseSettings` and built with a layered, composable design.

## Structure

| File | Purpose |
|------|---------|
| `__init__.py` | Public entrypoint. Re-exports classes and creates the global `settings` singleton. |
| `settings_core.py` | Top-level `AppSettings` class. Composes LLM, workflow, and agent endpoint config. |
| `settings_core_agents.py` | `AgentEndpointsMixin` — ports and URLs for every A2A agent service. |
| `settings_llm.py` | `LLMSettings` — OpenRouter model, base URL, and API key. |
| `settings_workflow.py` | `WorkflowConfig` — workflow orchestration settings composed from mixins. |
| `settings_workflow_core.py` | `WorkflowConfigCore` — standalone core workflow config (budget, search, ranking, evidence). |
| `settings_workflow_ext.py` | `WorkflowConfigExt` — standalone extended workflow config (adds synthesis, output, checkpointing, PII, telemetry, cost attribution, A/B testing). |
| `settings_workflow_ext_defaults.py` | Default constants shared by `WorkflowConfigExt`. |
| `settings_workflow_ab.py` | `ABTestingMixin` — A/B testing toggle, sampling, winner metric, and composite weights. |
| `settings_workflow_budget_search_ranking.py` | `BudgetSearchRankingMixin` — budget, search provider, and ranking controls. |
| `settings_workflow_evidence_adversary_verification.py` | `EvidenceAdversaryVerificationMixin` — evidence chunking, adversary trigger, and verification thresholds. |
| `settings_workflow_synthesis_output_checkpointing_pii.py` | `SynthesisOutputCheckpointingPIIMixin` — synthesis streaming, output format, checkpoint stages, and PII handling. |
| `settings_workflow_telemetry.py` | `TelemetryMixin` — OpenTelemetry, Prometheus, trace logs, and cost attribution tags. |
| `settings_dotenv_keys.py` | Canonical set of expected `.env` keys for validation. |
| `settings_validation.py` | Helpers that warn when unknown keys appear in `.env`. |

## Config Layering

Settings compose from three namespaces into a single `AppSettings` instance:

```
AppSettings
├── Core app fields          (unprefixed)
├── AgentEndpointsMixin      (unprefixed *_PORT / *_URL)
├── llm: LLMSettings         (LLM_* prefix)
└── workflow: WorkflowConfig (WF_* prefix)
```

### Core application fields

These live directly on `AppSettings` and have no prefix:

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `log_level` | `LOG_LEVEL` | `DEBUG` | |
| `mesop_port` | `MESOP_PORT` | `32123` | |
| `workflow_timeout` | `WORKFLOW_TIMEOUT` | `180.0` | |
| `tavily_api_key` | `TAVILY_API_KEY` | `""` | Required at runtime |
| `brave_api_key` | `BRAVE_API_KEY` | `""` | Required at runtime |
| `search_max_results` | `SEARCH_MAX_RESULTS` | `5` | `1 <= x <= 25` |
| `searcher_max_steps` | `SEARCHER_MAX_STEPS` | `5` | `1 <= x <= 20` |
| `research_max_rounds` | `RESEARCH_MAX_ROUNDS` | `5` | `1 <= x <= 10` |

### Agent endpoints

`AgentEndpointsMixin` provides `*_port` and `*_url` pairs for each A2A service. Ports default to the `10001`–`10012` range. URLs default to `http://localhost:<port>`.

Supported agents: `preprocessor`, `clarifier`, `planner`, `searcher`, `ranker`, `reader`, `evidence_deduplicator`, `fact_checker`, `adversary`, `synthesizer`, `critic`, `postprocessor`.

Example env vars: `PLANNER_PORT`, `PLANNER_URL`, `SEARCHER_PORT`, `SEARCHER_URL`.

### LLM settings

`LLMSettings` uses the `LLM_` prefix:

| Field | Env Var | Default |
|-------|---------|---------|
| `model` | `LLM_MODEL` | `openrouter/elephant-alpha` |
| `base_url` | `LLM_BASE_URL` | `https://openrouter.ai/api/v1` |
| `api_key` | `LLM_API_KEY` | `""` |

### Workflow settings

`WorkflowConfig` inherits from five mixins plus `BaseSettings`. Its env prefix is `WF_`. Fields are namespaced with double underscores, so the env var for `budget_max_rounds` is `WF_BUDGET__MAX_ROUNDS`.

**Budget**

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `budget_max_rounds` | `WF_BUDGET__MAX_ROUNDS` | `5` | `>= 1` |
| `budget_max_tokens` | `WF_BUDGET__MAX_TOKENS` | `200000` | `>= 1000` |
| `budget_max_wall_seconds` | `WF_BUDGET__MAX_WALL_SECONDS` | `180` | `>= 10` |
| `budget_max_http_calls` | `WF_BUDGET__MAX_HTTP_CALLS` | `50` | `>= 1` |
| `budget_min_marginal_evidence` | `WF_BUDGET__MIN_MARGINAL_EVIDENCE` | `2` | `>= 0` |
| `budget_max_critic_revision_loops` | `WF_BUDGET__MAX_CRITIC_REVISION_LOOPS` | `2` | `>= 0` |

**Search**

| Field | Env Var | Default |
|-------|---------|---------|
| `search_providers` | `WF_SEARCH__PROVIDERS` | `["tavily", "brave", "ddg"]` |
| `search_parallel` | `WF_SEARCH__PARALLEL` | `true` |
| `search_max_results_per_provider` | `WF_SEARCH__MAX_RESULTS_PER_PROVIDER` | `5` |

**Ranking**

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `ranking_enabled` | `WF_RANKING__ENABLED` | `true` | |
| `ranking_fetch_budget` | `WF_RANKING__FETCH_BUDGET` | `8` | `>= 1` |
| `ranking_diversity_penalty` | `WF_RANKING__DIVERSITY_PENALTY` | `0.3` | `0.0 <= x <= 1.0` |
| `ranking_freshness_weight_default` | `WF_RANKING__FRESHNESS_WEIGHT_DEFAULT` | `0.2` | `0.0 <= x <= 1.0` |

**Evidence**

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `evidence_deduplication` | `WF_EVIDENCE__DEDUPLICATION` | `true` | |
| `evidence_chunk_size` | `WF_EVIDENCE__CHUNK_SIZE` | `1000` | `>= 100` |
| `evidence_chunk_overlap` | `WF_EVIDENCE__CHUNK_OVERLAP` | `200` | `>= 0` |
| `evidence_source_independence` | `WF_EVIDENCE__SOURCE_INDEPENDENCE` | `true` | |

**Adversary**

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `adversary_enabled` | `WF_ADVERSARY__ENABLED` | `true` | |
| `adversary_trigger` | `WF_ADVERSARY__TRIGGER` | `on_tentative_supported` | |
| `adversary_inversion_query_count` | `WF_ADVERSARY__INVERSION_QUERY_COUNT` | `3` | `1 <= x <= 10` |
| `adversary_counter_expert_lookup` | `WF_ADVERSARY__COUNTER_EXPERT_LOOKUP` | `true` | |

**Verification**

| Field | Env Var | Default | Constraints |
|-------|---------|---------|-------------|
| `verification_cache_results` | `WF_VERIFICATION__CACHE_RESULTS` | `true` | |
| `verification_confidence_auto_accept_threshold` | `WF_VERIFICATION__CONFIDENCE_AUTO_ACCEPT_THRESHOLD` | `0.9` | `0.0 <= x <= 1.0` |
| `verification_short_circuit_when_adversary_holds` | `WF_VERIFICATION__SHORT_CIRCUIT_WHEN_ADVERSARY_HOLDS` | `true` | |

**Synthesis**

| Field | Env Var | Default |
|-------|---------|---------|
| `synthesis_streaming` | `WF_SYNTHESIS__STREAMING` | `sse_via_coordinator` |
| `synthesis_tentative_snapshot_strategy` | `WF_SYNTHESIS__TENTATIVE_SNAPSHOT_STRATEGY` | `cheap_template_every_round_plus_full_on_exit` |

**Output**

| Field | Env Var | Default |
|-------|---------|---------|
| `output_formats` | `WF_OUTPUT__FORMATS` | `["markdown", "json"]` |
| `output_citation_style` | `WF_OUTPUT__CITATION_STYLE` | `hyperlinked_footnotes` |

**Checkpointing**

| Field | Env Var | Default |
|-------|---------|---------|
| `checkpointing_enabled` | `WF_CHECKPOINTING__ENABLED` | `true` |
| `checkpointing_stages` | `WF_CHECKPOINTING__STAGES` | `["plan", "verify", "adversary_gate", "synthesize"]` |

**PII**

| Field | Env Var | Default |
|-------|---------|---------|
| `pii_query_egress` | `WF_PII__QUERY_EGRESS` | `hash_with_session_key` |
| `pii_evidence_ingest` | `WF_PII__EVIDENCE_INGEST` | `mask` |
| `pii_checkpoint_write` | `WF_PII__CHECKPOINT_WRITE` | `mask` |
| `pii_pre_synthesis` | `WF_PII__PRE_SYNTHESIS` | `mask` |

**Telemetry**

| Field | Env Var | Default |
|-------|---------|---------|
| `telemetry_opentelemetry` | `WF_TELEMETRY__OPENTELEMETRY` | `true` |
| `telemetry_prometheus` | `WF_TELEMETRY__PROMETHEUS` | `true` |
| `telemetry_trace_log` | `WF_TELEMETRY__TRACE_LOG` | `true` |
| `telemetry_trace_ids` | `WF_TELEMETRY__TRACE_IDS` | `["session_id", "trace_id", "span_id"]` |

**Cost attribution**

| Field | Env Var | Default |
|-------|---------|---------|
| `cost_attribution_enabled` | `WF_COST_ATTRIBUTION__ENABLED` | `true` |
| `cost_attribution_tags` | `WF_COST_ATTRIBUTION__TAGS` | `["session_id", "claim_id", "user_id"]` |

**A/B testing**

| Field | Env Var | Default |
|-------|---------|---------|
| `ab_testing_enabled` | `WF_AB_TESTING__ENABLED` | `true` |
| `ab_testing_sampling` | `WF_AB_TESTING__SAMPLING` | `per_query_class_sticky` |
| `ab_testing_winner_metric` | `WF_AB_TESTING__WINNER_METRIC` | `weighted_composite` |
| `ab_testing_weights` | `WF_AB_TESTING__WEIGHTS` | `claim_recall: 0.35, citation_accuracy: 0.35, latency: 0.15, cost: 0.15` |

Weights are validated to sum to approximately `1.0` (within `0.01`).

## Alternate workflow config classes

In addition to `WorkflowConfig` (the mixin-based class used in `AppSettings`), the module provides two standalone alternatives:

- `WorkflowConfigCore` — single class with the same budget, search, ranking, and evidence fields.
- `WorkflowConfigExt` — single class with every field from `WorkflowConfigCore` plus synthesis, output, checkpointing, PII, telemetry, cost attribution, and A/B testing.

Both use the `WF_` env prefix. They are available for consumers that prefer a flat class over the mixin composition used by `WorkflowConfig`.

## Validation and `.env` contract

`AppSettings` runs two model validators after construction:

1. **`validate_dotenv_contract`** — warns when `.env` contains unknown keys. The expected key set is defined in `settings_dotenv_keys.py` and covers all core fields, LLM-prefixed fields, WF-prefixed fields, agent `*_PORT` / `*_URL` fields, and passthrough prefixes `MESOP_*`.
2. **`require_api_credentials`** — raises `ValueError` if `LLM_API_KEY`, `TAVILY_API_KEY`, or `BRAVE_API_KEY` are empty.

The `.env` file is resolved relative to the project root (`src/a2a_research/backend/.env`).

## Usage

Import the pre-built singleton:

```python
from a2a_research.backend.core.settings import settings

print(settings.llm.model)
print(settings.workflow.budget_max_rounds)
print(settings.planner_url)
```

Or instantiate classes directly:

```python
from a2a_research.backend.core.settings import LLMSettings, WorkflowConfig

llm = LLMSettings()
workflow = WorkflowConfig()
```
