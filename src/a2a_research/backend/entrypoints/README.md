# Entrypoints

Application entry points for starting backend services.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports `main` from `launcher.py` |
| `launcher.py` | Starts all HTTP agent services in one process |
| `README.md` | Directory documentation |

## Runnable modules

### `launcher.py`

`launcher.py` builds HTTP apps for these services:

- `planner`
- `searcher`
- `reader`
- `fact-checker`
- `synthesizer`

It creates one `uvicorn.Server` per service, starts each server in a daemon thread, logs startup, and keeps the process alive until a server stops or `KeyboardInterrupt` is received.

The module also supports direct execution via:

```bash
python -m a2a_research.backend.entrypoints.launcher
```

### `__init__.py`

This package exposes `main` as its public entrypoint:

```python
from a2a_research.backend.entrypoints import main
```

## Make targets

The launcher is used by these Make targets:

```bash
make serve-all
make serve-planner
make serve-searcher
make serve-reader
make serve-fact-checker
make serve-synthesizer
```

`make serve-all` starts all services together. The service-specific targets start one agent HTTP server at a time using that service's configured port.

## Notes

- The launcher uses configured ports from `a2a_research.backend.core.settings`.
- Each service is started as an HTTP server ready to accept A2A task requests.
