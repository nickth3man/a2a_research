# Implementation Plan: flow.md Architecture + Legacy Cleanup

## Context

The codebase has two workflow engines living side-by-side:
- **v1 coordinator** (`coordinator.py`, `coordinator_drive.py`, etc.) — a simple 5-agent sequential pipeline. The API (`api.py`) currently calls this one.
- **v2 engine** (`workflow_engine.py`, `engine.py`, `engine_setup.py`, `engine_loop.py`, etc.) — a 12-agent claim-centric DAG engine. Exists but is **not wired to the API**.

The target (`flow.md`) maps exactly onto the v2 engine's structure, extended with: structured `ErrorEnvelope` diagnostics, a richer SSE event vocabulary (`warning`, `retrying`, `degraded_mode`, `final_diagnostics`), back-channel agent payloads (CLR↔PRE, PLN↔CLR, FAC↔PLN, ADV↔FAC, etc.), registry snapshots, and a context bus. Git tracks history — no versioning suffixes needed anywhere.

**Kaizen principle applied**: build incrementally in phases; each phase leaves the system runnable. Reuse existing engine modules — only extend, don't rewrite.

---

## Phase 0 — Delete v1 coordinator (legacy)

**Files to delete entirely:**
```
src/a2a_research/backend/workflow/coordinator.py
src/a2a_research/backend/workflow/coordinator_drive.py
src/a2a_research/backend/workflow/coordinator_planner.py
src/a2a_research/backend/workflow/coordinator_searcher.py
src/a2a_research/backend/workflow/coordinator_reader.py
src/a2a_research/backend/workflow/coordinator_fact_checker.py
src/a2a_research/backend/workflow/coordinator_synthesizer.py
src/a2a_research/backend/workflow/coordinator_helpers.py
src/a2a_research/backend/agents/stubs/clarifier/          ← duplicate of pocketflow/clarifier
src/a2a_research/backend/agents/pocketflow/adversary/     ← WIP nodes, no main.py, not mounted
```

**Files to rename:**
```
scripts/extract_prompts_v2.py → scripts/extract_prompts.py
```

**Note:** `coordinator_helpers.mark_running_failed` already exists verbatim in `workflow/status.py`. No migration needed.

---

## Phase 1 — Strip all "v2" naming

Rename identifiers in-place (no logic changes):

| Old name | New name | Files affected |
|---|---|---|
| `run_workflow_v2_async` | `run_workflow_async` | `workflow_engine.py`, `workflow/__init__.py`, tests |
| `run_workflow_v2_sync` | `run_workflow_sync` | same |
| `drive_v2` | `drive` | `engine.py`, `workflow_engine.py` |
| `emit_v2` | `emit_step` | `status.py`, `engine.py`, `engine_setup.py`, `engine_loop.py`, `engine_final.py` |
| `STEP_INDEX_V2` | `STEP_INDEX` | `definitions.py`, `status.py`, `workflow_engine.py` |
| `TOTAL_STEPS_V2` | `TOTAL_STEPS` | `definitions.py`, `status.py` |

Update module docstrings that reference "v1"/"v2" to be version-neutral.

**`workflow/__init__.py` after cleanup:**
```python
from a2a_research.backend.workflow.workflow_engine import (
    run_workflow_async,
    run_workflow_sync,
)
__all__ = ["run_workflow_async", "run_workflow_sync"]
```

---

## Phase 2 — Wire API to the claim-centric engine

**File:** `src/a2a_research/backend/entrypoints/api.py`

Currently imports `coordinator_drive.drive` and `coordinator_helpers.mark_running_failed`. Replace:

```python
# Remove:
from a2a_research.backend.workflow.coordinator_drive import drive
from a2a_research.backend.workflow.coordinator_helpers import mark_running_failed

# Add:
from a2a_research.backend.workflow.workflow_engine import run_workflow_async
from a2a_research.backend.workflow.status import mark_running_failed
```

`_run_workflow()` in `api.py` currently creates its own session and calls `drive(session, client, query)`. The new `run_workflow_async(query, progress_queue)` handles session creation internally. Refactor `_run_workflow` to call `run_workflow_async` and return its `ResearchSession` result. The `Bus` registration moves into `run_workflow_async` (already there).

---

## Phase 3 — New models: `ErrorEnvelope` + ResearchSession updates

### 3a. New file: `src/a2a_research/backend/core/models/errors.py`

```python
class ErrorSeverity(str, Enum):
    FATAL = "fatal"
    WARNING = "warning"
    DEGRADED = "degraded"

class ErrorCode(str, Enum):
    QUERY_REJECTED = "QUERY_REJECTED"
    LOW_CLAIM_COVERAGE = "LOW_CLAIM_COVERAGE"
    PLANNER_EMPTY = "PLANNER_EMPTY"
    NO_HITS = "NO_HITS"
    ALL_URLS_FILTERED = "ALL_URLS_FILTERED"
    UNREADABLE_PAGES = "UNREADABLE_PAGES"
    BUDGET_EXHAUSTED_AFTER_GATHER = "BUDGET_EXHAUSTED_AFTER_GATHER"
    BUDGET_EXHAUSTED_AFTER_VERIFY = "BUDGET_EXHAUSTED_AFTER_VERIFY"
    BUDGET_EXHAUSTED_AFTER_SNAPSHOT = "BUDGET_EXHAUSTED_AFTER_SNAPSHOT"
    DIAGNOSTIC_SUMMARY = "DIAGNOSTIC_SUMMARY"

class ErrorEnvelope(BaseModel):
    role: AgentRole | None
    code: ErrorCode
    severity: ErrorSeverity
    retryable: bool = False
    root_cause: str = ""
    partial_results: dict[str, Any] = {}
    remediation: str = ""
    trace_id: str = ""
    upstream_errors: list["ErrorEnvelope"] = []
```

Export from `core/models/__init__.py`.

### 3b. Update `src/a2a_research/backend/core/models/session.py`

Add to `ResearchSession`:
```python
trace_id: str = Field(default_factory=lambda: uuid4().hex)
error_ledger: list[ErrorEnvelope] = Field(default_factory=list)
```

---

## Phase 4 — New SSE event types

### 4a. `src/a2a_research/backend/core/progress/progress_types.py`

Add to `ProgressPhase`:
```python
WARNING = "warning"
RETRYING = "retrying"
DEGRADED_MODE = "degraded_mode"
FINAL_DIAGNOSTICS = "final_diagnostics"
```

Add optional field to `ProgressEvent`:
```python
envelope: ErrorEnvelope | None = None
```

### 4b. Add helper to `workflow/status.py`

```python
def emit_envelope(
    session_id: str, envelope: ErrorEnvelope, session: ResearchSession
) -> None:
    """Append envelope to ledger and emit the matching SSE phase."""
    session.error_ledger.append(envelope)
    phase = {
        ErrorSeverity.FATAL: ProgressPhase.FINAL_DIAGNOSTICS,
        ErrorSeverity.WARNING: ProgressPhase.WARNING,
        ErrorSeverity.DEGRADED: ProgressPhase.DEGRADED_MODE,
    }[envelope.severity]
    emit_step(session_id, envelope.role, phase, envelope.code.value,
              detail=envelope.root_cause, envelope=envelope)
```

### 4c. Update `api.py` SSE serialization

Map new phases to SSE event names:
- `ProgressPhase.WARNING` → `event: warning`
- `ProgressPhase.RETRYING` → `event: retrying`
- `ProgressPhase.DEGRADED_MODE` → `event: degraded_mode`
- `ProgressPhase.FINAL_DIAGNOSTICS` → `event: final_diagnostics`
- Existing phases → `event: progress` (unchanged)

Update `_serialize_result` to include:
```python
"diagnostics": [_serialize_envelope(e) for e in session.error_ledger],
```

Add `_serialize_envelope(e: ErrorEnvelope) -> dict` helper.

---

## Phase 5 — Registry snapshot at workflow start

**File:** `src/a2a_research/backend/core/a2a/registry.py`

Add `build_snapshot()` method:
```python
def build_snapshot(self) -> dict[str, Any]:
    """Return capability map: role → {url, capabilities, timeouts}."""
    ...
```

**File:** `src/a2a_research/backend/workflow/engine.py` (formerly `drive_v2`)

After session init, emit registry snapshot to BUS:
```python
snapshot = registry.build_snapshot()
emit_step(session.id, None, ProgressPhase.STEP_STARTED, "registry_snapshot",
          detail=json.dumps({"agent_count": len(snapshot)}))
```

---

## Phase 6 — Setup stage: back-channels + error envelopes

**File:** `src/a2a_research/backend/workflow/engine_setup.py`

### Preprocessor → Clarifier back-channel
Pass PRE output fields into CLR payload:
```python
clarify_payload = {
    "query": sanitized_query,
    "query_class": query_class,
    "session_id": session.id,
    "trace_id": session.trace_id,
    # Back-channel from PRE:
    "normalization_rationale": preprocess_result.get("normalization_notes", ""),
    "risky_spans": preprocess_result.get("risky_spans", []),
    "domain_hints": domain_hints,
}
```

### PRE partial failure → ErrorEnvelope
```python
if preprocess_result.get("warning"):
    emit_envelope(session.id, ErrorEnvelope(
        role=AgentRole.PREPROCESSOR, code=ErrorCode.QUERY_REJECTED,
        severity=ErrorSeverity.WARNING, retryable=False,
        root_cause=preprocess_result.get("warning", ""),
    ), session)
```

### Query rejection (abort) → fatal ErrorEnvelope + final_diagnostics
```python
emit_envelope(session.id, ErrorEnvelope(
    role=AgentRole.PREPROCESSOR, code=ErrorCode.QUERY_REJECTED,
    severity=ErrorSeverity.FATAL, retryable=False,
    root_cause="Query classified as unanswerable or sensitive.",
    trace_id=session.trace_id,
), session)
# emit final_diagnostics SSE before returning None
```

### Clarifier → Planner back-channel
```python
plan_payload = {
    "query": committed_interpretation,
    "domain_hints": domain_hints,
    "session_id": session.id,
    "trace_id": session.trace_id,
    # Back-channel from CLR:
    "ambiguity_constraints": clarify_result.get("ambiguity_notes", ""),
    "interpretation_rationale": clarify_result.get("rejected_interpretations", []),
}
```

### PLN LOW_CLAIM_COVERAGE warning
```python
if len(claims) < budget.min_claims_threshold:  # e.g. 2
    emit_envelope(session.id, ErrorEnvelope(
        role=AgentRole.PLANNER, code=ErrorCode.LOW_CLAIM_COVERAGE,
        severity=ErrorSeverity.WARNING, retryable=True,
        root_cause=f"Planner produced only {len(claims)} claim(s).",
        trace_id=session.trace_id,
    ), session)
```

### PLN PLANNER_EMPTY → fatal
```python
emit_envelope(session.id, ErrorEnvelope(
    role=AgentRole.PLANNER, code=ErrorCode.PLANNER_EMPTY,
    severity=ErrorSeverity.FATAL, retryable=False,
    trace_id=session.trace_id,
), session)
```

---

## Phase 7 — Gather stage: back-channels + error envelopes

**File:** `src/a2a_research/backend/workflow/engine_gather.py`

### SEA→PLN query refinement (pass alternate formulations)
SEA payload already receives `queries`. After SEA result, extract `alternate_formulations` and pass to next SEA invocation (store on session or claim_state). Also pass `replan_hints` from prior rounds.

### SEA result → RNK back-channel
```python
rnk_payload = {
    ...,
    "source_trust_priors": sea_result.get("source_trust_priors", {}),
    "duplicate_domain_hints": sea_result.get("duplicate_domain_hints", []),
}
```

### RNK result → REA back-channel (dead URL reporting)
```python
rea_payload = {
    ...,
    "backup_urls": rnk_result.get("backup_urls", []),
    "revised_order": rnk_result.get("revised_order", []),
}
```

### REA result → DED back-channel (fingerprints)
```python
ded_payload = {
    ...,
    "extraction_fingerprints": rea_result.get("fingerprints", {}),
    "chunk_ids": rea_result.get("chunk_ids", []),
}
```

### Error envelopes for gather failures

| Condition | Code | Severity | SSE event |
|---|---|---|---|
| `sea_result.get("hits") == []` | `NO_HITS` | `degraded` | `degraded_mode` |
| `rnk_result.get("selected_urls") == []` | `ALL_URLS_FILTERED` | `degraded` | `degraded_mode` |
| `rea_result.get("readable_pages") == []` | `UNREADABLE_PAGES` | `degraded` | `retrying` |
| budget exhausted after gather | `BUDGET_EXHAUSTED_AFTER_GATHER` | `degraded` | `degraded_mode` |

All call `emit_envelope(session.id, envelope, session)` and return early from gather.

---

## Phase 8 — Verify stage: FAC/ADV back-channels + error envelopes

**File:** `src/a2a_research/backend/workflow/engine_verify.py`

### FAC payload additions
```python
fac_payload = {
    ...,
    "claim_dag": claim_state.dag.model_dump(mode="json"),
    "trace_id": session.trace_id,
    # Supporting excerpts already in pages; pass extraction_confidence explicitly:
    "extraction_confidence": {p.url: p.confidence for p in pages},
}
```

### ADV: direct calls to SEA and REA for counter-evidence
When `fac_result.get("tentatively_supported_claims")` is non-empty:
```python
adv_sea_result = await _run_agent(session, client, AgentRole.SEARCHER, {
    "queries": adv_result.get("counter_queries", []),
    "session_id": session.id,
    "trace_id": session.trace_id,
    "mode": "counter_evidence",
})
adv_rea_result = await _run_agent(session, client, AgentRole.READER, {
    "urls": adv_sea_result.get("hits", []),
    "session_id": session.id,
    "trace_id": session.trace_id,
    "mode": "counter_evidence",
})
adv_payload["counter_hits"] = adv_sea_result.get("hits", [])
adv_payload["counter_pages"] = adv_rea_result.get("pages", [])
```

### Error envelopes for verify failures

| Condition | Code | Severity |
|---|---|---|
| budget exhausted after FAC+ADV | `BUDGET_EXHAUSTED_AFTER_VERIFY` | `degraded` |

---

## Phase 9 — Snapshot and replan loop

**File:** `src/a2a_research/backend/workflow/engine_loop.py`

### SYN tentative snapshot
Pass `error_ledger` as diagnostics:
```python
snapshot_payload = {
    ...,
    "mode": "tentative",
    "diagnostics": [e.model_dump(mode="json") for e in session.error_ledger],
    "trace_id": session.trace_id,
}
```

### BUDGET_EXHAUSTED_AFTER_SNAPSHOT
```python
emit_envelope(session.id, ErrorEnvelope(
    role=AgentRole.SYNTHESIZER,
    code=ErrorCode.BUDGET_EXHAUSTED_AFTER_SNAPSHOT,
    severity=ErrorSeverity.DEGRADED, retryable=False,
    trace_id=session.trace_id,
), session)
```

---

## Phase 10 — Final stage: SYN/CRI/POS + final_diagnostics

**File:** `src/a2a_research/backend/workflow/engine_final.py`

### SYN final — pass provenance_tree + error_ledger
```python
syn_payload = {
    ...,
    "provenance_tree": provenance_tree.model_dump(mode="json"),
    "tentative_report": session.tentative_report.model_dump(mode="json") if session.tentative_report else None,
    "diagnostics": [e.model_dump(mode="json") for e in session.error_ledger],
    "trace_id": session.trace_id,
}
```

### CRI → SYN revision loop (already partially exists)
Pass `error_ledger` to CRI:
```python
cri_payload = {
    ...,
    "diagnostics": [e.model_dump(mode="json") for e in session.error_ledger],
    "trace_id": session.trace_id,
}
```

### POS — receives error_ledger, returns diagnostic_appendix
```python
pos_payload = {
    ...,
    "error_ledger": [e.model_dump(mode="json") for e in session.error_ledger],
    "output_formats": ["markdown", "json"],
    "citation_style": "hyperlinked_footnotes",
    "trace_id": session.trace_id,
}
pos_result = await _run_agent(session, client, AgentRole.POSTPROCESSOR, pos_payload)
# Merge condensed diagnostic appendix back into session
if condensed := pos_result.get("diagnostic_appendix"):
    session.error_ledger.append(ErrorEnvelope(
        role=AgentRole.POSTPROCESSOR, code=ErrorCode.DIAGNOSTIC_SUMMARY,
        severity=ErrorSeverity.WARNING, root_cause=str(condensed),
    ))
```

### Emit `final_diagnostics` SSE before returning
```python
emit_step(session.id, None, ProgressPhase.FINAL_DIAGNOSTICS, "workflow_complete",
          detail=json.dumps({"error_count": len(session.error_ledger)}))
```

---

## Phase 11 — Frontend SSE + type updates

**File:** `frontend/src/services/api.ts`

Add event listeners for new SSE types:
```typescript
es.addEventListener('warning', (e) => callbacks.onWarning?.(JSON.parse(e.data)));
es.addEventListener('retrying', (e) => callbacks.onRetrying?.(JSON.parse(e.data)));
es.addEventListener('degraded_mode', (e) => callbacks.onDegraded?.(JSON.parse(e.data)));
es.addEventListener('final_diagnostics', (e) => callbacks.onFinalDiagnostics?.(JSON.parse(e.data)));
```

**File:** `frontend/src/types/index.ts`

Add:
```typescript
interface DiagnosticItem {
  role: string | null;
  code: string;
  severity: 'fatal' | 'warning' | 'degraded';
  retryable: boolean;
  root_cause: string;
  remediation: string;
}
// Update ResultMsg to include:
diagnostics: DiagnosticItem[];
```

**File:** `frontend/src/App.tsx`

Add state: `diagnostics`, `degradedRoles`, `warnings`. Wire to new callbacks.

**File:** `frontend/src/components/LoadingState.tsx`

Show warning/degraded indicator on agent nodes that emitted envelopes.

**File:** `frontend/src/components/ResultsState.tsx`

Add "Known limitations" / diagnostics section if `diagnostics.length > 0`.

---

## Phase 12 — Test updates

Files that import renamed symbols or deleted modules:

| Test file | Change needed |
|---|---|
| Any test importing `run_workflow_v2_async` | → `run_workflow_async` |
| Any test importing `coordinator_drive` / `coordinator_helpers` | → update to new engine |
| Add `tests/test_error_envelope.py` | Test ErrorEnvelope construction, ledger append, SSE serialize |
| Add `tests/test_sse_events.py` | Test new SSE event phases serialize correctly |

---

## Critical files (read before editing)

| File | Role |
|---|---|
| `src/a2a_research/backend/workflow/engine_setup.py` | Setup stage (Phase 6) |
| `src/a2a_research/backend/workflow/engine_gather.py` | Gather stage (Phase 7) |
| `src/a2a_research/backend/workflow/engine_verify.py` | Verify stage (Phase 8) |
| `src/a2a_research/backend/workflow/engine_loop.py` | Loop + snapshot (Phase 9) |
| `src/a2a_research/backend/workflow/engine_final.py` | Final stage (Phase 10) |
| `src/a2a_research/backend/workflow/status.py` | emit_step + emit_envelope |
| `src/a2a_research/backend/workflow/definitions.py` | STEP_INDEX rename |
| `src/a2a_research/backend/entrypoints/api.py` | SSE serialization + wiring |
| `src/a2a_research/backend/core/models/session.py` | trace_id + error_ledger |
| `src/a2a_research/backend/core/progress/progress_types.py` | New ProgressPhase values |
| `src/a2a_research/backend/core/a2a/registry.py` | build_snapshot() |

---

## Reusable utilities (don't re-implement)

- `workflow/status.py::set_status()` — reuse for all agent status updates
- `workflow/status.py::mark_running_failed()` — reuse in api.py
- `workflow/coerce.py::coerce_claims/coerce_dag/coerce_report` — reuse in setup stage
- `workflow/reports.py::abort_report/planner_failed_report` — reuse, add error_ledger param
- `core/progress/progress_emit_core.py::emit()` — the underlying emitter; emit_step wraps it
- `core/a2a/client.py::A2AClient.send()` — all inter-agent calls go through this

---

## Verification

1. **Unit tests**: `pytest tests/ -x` — all existing tests pass after Phase 0-2
2. **Error model tests**: `pytest tests/test_error_envelope.py` after Phase 3
3. **SSE event tests**: `pytest tests/test_sse_events.py` after Phase 4
4. **Integration smoke test**: Start backend (`make dev` or `uvicorn`), POST `/api/research` with a test query, watch SSE stream for `progress`, `warning`, `degraded_mode`, and `result` events
5. **Frontend**: `npm run dev` in `frontend/`, submit a query, verify LoadingState shows warning badges and ResultsState shows diagnostics section
6. **Type check**: `mypy src/` — no new errors
7. **Lint**: `ruff check src/` — no new violations