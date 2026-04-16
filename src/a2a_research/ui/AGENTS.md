# UI KNOWLEDGE BASE

## OVERVIEW
Mesop-only surface. `app.py` is the single page; everything else supports rendering, state derivation, or reusable components.

## STRUCTURE
```text
ui/
├── app.py              # AppState, main_page, submit/retry handlers, Windows static-file patch
├── components/         # public UI components re-exported via components/__init__.py
├── session_state.py    # derived-state helpers like has_results / has_progress
├── data_access.py      # presentation-facing accessors such as agent labels
├── formatting.py       # UI formatting helpers
├── primitives.py       # lower-level Mesop primitives
├── theme.py            # style composition
└── tokens.py           # design tokens / constants
```

## WHERE TO LOOK
| Task | Location | Notes |
|---|---|---|
| Page entrypoint | `app.py` | only `@me.page` in the repo |
| Query submit flow | `app.py::_on_submit` | async generator; bridges workflow progress to UI state |
| Component exports | `components/__init__.py` | import from here, not leaf files, when possible |
| Empty/header/instruction sections | `components/page_sections.py` | page scaffolding |
| Timeline/loading/progress UI | `components/timeline.py`, `components/banners.py`, `components/progress_bar.py` | loading and per-agent status |
| State predicates | `session_state.py` | use existing helpers before adding more view logic to `app.py` |
| Visual constants | `tokens.py` | central place for page spacing, fonts, example queries |

## CONVENTIONS
- `AppState.session` must stay a concrete `ResearchSession`; optional/union session fields break Mesop serialization.
- Keep Mesop runtime workarounds centralized in `app.py`; current example is the `send_file_compressed` Windows patch.
- UI orchestration consumes workflow progress through queue-draining, not direct polling loops spread across components.
- `components/` is the public component boundary; `app.py` should compose exported components, not rebuild their internals.

## ANTI-PATTERNS
- Do not create additional pages unless the routing model truly changes; current app assumes one page.
- Do not move workflow execution into components; `app.py` owns submit/retry side effects.
- Do not duplicate display-state checks in components when `session_state.py` already models them.
- Do not remove `MESOP_STATE_SESSION_BACKEND=memory` from local dev workflow unless hot-reload behavior changes upstream.

## TESTING
- UI tests depend on `tests/conftest.py` Mesop runtime stubs (`stub_mesop_component_runtime`, `stub_mesop_box_runtime`).
- State is commonly injected with `patch.object(app_mod.me, "state", return_value=SimpleNamespace(...))`.
- Existing coverage is split across `test_ui_app.py`, `test_ui_components.py`, `test_ui_main_page.py`, `test_ui_session_state.py`, and `test_ui_theme.py`; extend the nearest file instead of creating one-off UI test files.

## HOTSPOTS
- `app.py` (~500 lines) is the UI chokepoint: page tree, state, handlers, progress bridge, and framework patch all live there.
- `tokens.py` is large because visual constants and example content are centralized there by design.
