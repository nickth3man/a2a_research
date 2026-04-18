# Progress Events

## Overview

Progress events are local coordinator-process events used for the Mesop timeline.

They are **not** cross-service A2A streaming events.

## Components

- `Bus` — in-process session-id → queue registry
- `emit()` — convenience helper for enqueuing `ProgressEvent`
- `drain_progress_while_running()` — async generator used by the UI
- `AppState` progress fields — current rendered state for the UI

## Event model

Important fields:

- `session_id`
- `phase` (`step_started`, `step_substep`, `step_completed`, `step_failed`)
- `role`
- `step_index`, `total_steps`
- `substep_label`
- `detail`

## Flow

1. UI submit creates a queue
2. coordinator registers it in `Bus`
3. coordinator and executors emit progress by `session_id`
4. UI drains the queue while the workflow task runs
5. coordinator sends trailing sentinel `None` and unregisters the queue

## Adding a new event

1. choose the owning role
2. choose whether it is a step start, substep, completion, or failure
3. emit via `emit(session_id, ...)`
4. keep labels concise; use `detail` for longer context
5. ensure the UI can tolerate the event without custom code if possible

## Design constraint

The progress bus is intentionally local to the coordinator/UI process. HTTP A2A services remain independently testable and do not need direct knowledge of Mesop state.
