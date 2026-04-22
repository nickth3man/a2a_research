# Core

Shared backend infrastructure shell for the A2A research pipeline. This directory holds the cross-cutting code that every other backend package imports: Pydantic models, A2A protocol bindings, typed configuration, structured logging, real-time progress tracking, and low-level utilities.

## Role in the Backend

`backend/core/` is the dependency root of the backend. Agents, workflow orchestration, LLM providers, and external tools all import from here. It intentionally contains no business logic about research, planning, or verification. It only defines the vocabulary, wiring, and observability primitives that those layers share.

## Structure

| Directory | Purpose |
|-----------|---------|
| `a2a/` | A2A (Agent-to-Agent) protocol implementation built on `a2a-sdk` |
| `logging/` | Structured logging setup, formatters, and stream redirection |
| `models/` | Pydantic domain models for claims, evidence, reports, sessions, and workflow state |
| `progress/` | Real-time progress events and queues consumed by the Mesop UI |
| `settings/` | Typed, environment-driven configuration split by domain |
| `utils/` | Low-level helpers for JSON parsing, timing, citations, and validation |

### a2a/

HTTP A2A layer that wraps the official `a2a-sdk` protocol types.

Key modules:
- `cards.py` — per-role `AgentCard` definitions for server advertisement and UI labels
- `client.py` — `A2AClient` for sending `Message` objects to HTTP A2A services
- `registry.py` — `AgentRegistry` that maps roles to endpoint URLs
- `proto.py` — core protocol definitions and message types
- `compat.py` — compatibility shims across A2A versions

Public exports from `a2a_research.backend.core.a2a` include `AGENT_CARDS`, `A2AClient`, `AgentRegistry`, `build_message`, `extract_text`, `extract_data_payloads`, `get_registry`, and `reset_registry`.

### logging/

Shared logging setup used across the entire application.

Key modules:
- `app_logging.py` — `setup_logging()` configures the root logger once; `get_logger()` and `log_event()` are the main interfaces
- `logging_formatters.py` — custom formatters and filters (prefix, A2A SDK, HTTP clients, Mesop server, warnings)
- `logging_streams.py` — `StreamToLogger` for redirecting `stdout`/`stderr` into the logging pipeline
- `exception_logging.py` — exception hook installation

When configured, logs are written to `logs/` with separate files for the application, A2A SDK, HTTP clients, Mesop server, captured stdio, and Python warnings.

### models/

Single source of truth for Pydantic domain models shared across agents, workflow, A2A, and the UI.

Key modules:
- `session.py` — `ResearchSession` (full pipeline state) and `AgentResult` (single agent output)
- `claims.py` — `Claim`, `ClaimDAG`, `ClaimDependency`, `ReplanReason`, `FreshnessWindow`
- `evidence.py` — `EvidenceUnit`, `Passage`, `CredibilitySignals`, `IndependenceGraph`
- `reports.py` — `ReportOutput`, `ReportSection`, `Citation`, `WebSource`
- `verification.py` — `ClaimVerification`, `ClaimState`, `VerificationRevision`
- `workflow.py` — `AgentDefinition`, `WorkflowBudget`, `BudgetConsumption`, `CircuitBreakerConfig`, `RetryPolicy`, `NoveltyTracker`
- `enums.py` — `AgentRole`, `AgentStatus`, `AgentCapability`, `TaskStatus`, `Verdict`, `ProvenanceEdgeType`, `ReplanReasonCode`
- `provenance.py` — `ProvenanceNode`, `ProvenanceEdge`, `ProvenanceTree`
- `fact_checker.py` — `FactCheckerOutput`

### progress/

Real-time progress events and queue helpers for live UI updates.

Key modules:
- `progress_emit.py` — `emit()`, `emit_handoff()`, `emit_tool_call()`, `emit_claim_verdict()`, `emit_prompt()`, `emit_llm_response()`, `emit_rate_limit()`
- `progress_types.py` — `ProgressEvent`, `ProgressQueue`, `ProgressReporter`, `ProgressPhase`, `ProgressGranularity`, plus context-based session tracking via `using_session()` and `current_session_id()`
- `progress_bus.py` — `Bus` for in-process event distribution
- `progress_utils.py` — `create_progress_reporter()` and `drain_progress_while_running()`

### settings/

Typed application settings loaded from `.env` and environment variables.

Key modules:
- `settings_core.py` — top-level `AppSettings` (agent endpoints, log level, Mesop port, API keys)
- `settings_llm.py` — `LLMSettings` (model id, base URL, API key, temperature)
- `settings_workflow.py` — `WorkflowConfig` with many split submodules for budget, telemetry, evidence adversary verification, synthesis output checkpointing, A/B flags, and search ranking
- `settings_validation.py` — `.env` key validation helpers
- `settings_dotenv_keys.py` — canonical list of expected environment keys

The module exports `settings`, a singleton `AppSettings` instance, plus `AppSettings`, `LLMSettings`, and `WorkflowConfig` classes.

### utils/

Low-level helpers with no internal dependencies to avoid circular imports.

Key modules:
- `json_utils.py` — `parse_json_safely()` extracts JSON from fenced code blocks or bare text
- `timing.py` — `perf_counter()` wrapper for consistent elapsed-time measurement
- `validation.py` — `to_float()` and `to_str_list()` coercion helpers
- `citation_sanitize.py` — citation cleaning utilities

Public exports: `perf_counter`, `to_float`, `to_str_list`.

## Design Principles

- **Type safety first** — All models use Pydantic with strict validation.
- **Centralized config** — Settings are hierarchical, typed, and driven by environment variables.
- **Observable** — Logging and progress are first-class concerns, not afterthoughts.
- **Protocol-native** — The A2A implementation follows the Google A2A specification and reuses the official `a2a-sdk` types where possible.
- **Zero internal coupling in utils** — `utils/` may not import from other backend packages to keep it safe as a lowest-level dependency.
