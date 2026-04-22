# Logging

Application logging infrastructure for the A2A research pipeline.

This package configures the root logger once, writes to multiple rotating file targets, and captures unhandled exceptions, warnings, and optional stdio redirection. All log output uses the same log level across every handler so records are never dropped inside the app.

## Setup

Import and call `setup_logging` before the rest of the application starts.

```python
from a2a_research.backend.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger("my.module")
```

`setup_logging` is idempotent. It creates a `logs/` directory in the current working directory and attaches handlers to the root logger. `get_logger` calls `setup_logging` automatically and returns a standard `logging.Logger`.

## Structured Logging

Use `log_event` to emit machine readable lines with an `event` name and a JSON payload.

```python
from a2a_research.backend.core.logging import log_event
import logging

log_event(
    logger,
    logging.INFO,
    "research.plan.completed",
    query="What is A2A?",
    steps=5,
)
```

Each structured line contains:

- `seq` — auto-incrementing sequence number
- `ts` — ISO 8601 timestamp in UTC
- `event` — the event name you provide
- `pid` — current process id
- `thread` — current thread name
- plus any extra keyword fields you pass

`log_event` normalizes field values before serializing:

- Primitives (`str`, `int`, `float`, `bool`, `None`) pass through unchanged
- `Path` objects become strings
- `dict`, `list`, `tuple`, and `set` are traversed recursively
- Objects with `.value`, `.model_dump()`, or `__dict__` are unpacked
- Everything else falls back to `repr()`

The default formatter used by every handler looks like this:

```
2026-04-22 12:34:56,789 INFO [a2a_research.backend] pid=12345 tid=140123456789 message
```

## Handlers and Filters

`setup_logging` attaches the following handlers to the root logger.

| Handler | Destination | Filter | Purpose |
|---------|-------------|--------|---------|
| Console | `sys.stderr` | none | Human readable terminal output |
| Everything | `logs/everything.log` | none | Full audit trail from every logger |
| App | `logs/app.log` | `PrefixFilter("a2a_research")` | Only this package |
| A2A SDK | `logs/a2a_sdk.log` | `A2aSdkFilter` | Third party `a2a` SDK (not `a2a_research`) |
| HTTP Clients | `logs/http_clients.log` | `HttpClientsFilter` | `httpx` and `httpcore` |
| Mesop Server | `logs/mesop_server.log` | `MesopServerFilter` | `mesop`, `flask`, `werkzeug`, `uvicorn` |
| Warnings | `logs/warnings.log` | `WarningsFilter` | Python `py.warnings` |

A separate `stdio_handler` writes to `logs/stdio.log` and also feeds into the everything handler. It is attached to dedicated `stdout` and `stderr` loggers so captured prints do not loop back to the console.

`setup_logging` also tunes several named loggers:

- `asyncio`, `mesop`, `werkzeug`, `flask` — level set to the configured global level
- `trafilatura.downloads` — set to `CRITICAL`
- `trafilatura.core` — set to `ERROR`

## Streams

`StreamToLogger` is a `TextIO` wrapper that copies every `write()` to the original stream and also logs the line.

```python
from a2a_research.backend.core.logging import redirect_stdio_to_logging

redirect_stdio_to_logging()
```

After this call, `sys.stdout` and `sys.stderr` are replaced. Output still appears in the terminal, but every non empty line is also sent to `logs/stdio.log` and `logs/everything.log` through the `stdout` and `stderr` loggers.

## Exception Hooks

`install_exception_hooks` is called automatically inside `setup_logging`. It patches two system hooks so crashes are always captured in the logs.

1. `sys.excepthook` — logs unhandled exceptions (except `KeyboardInterrupt`) to the `a2a_research.unhandled` logger with full traceback.
2. `threading.excepthook` — logs unhandled thread exceptions to the `a2a_research.threading` logger, then chains to the original hook.

For asyncio, call `install_asyncio_exception_logging` with an explicit loop (or let it fetch the running loop). It adds a handler that logs background task failures to `a2a_research.asyncio` and then calls the loop's default exception handler.

```python
from a2a_research.backend.core.logging.exception_logging import install_asyncio_exception_logging

install_asyncio_exception_logging()
```

## Files

- `app_logging.py` — `setup_logging`, `get_logger`, `redirect_stdio_to_logging`
- `logging_formatters.py` — `build_formatter`, `log_event`, and filter dataclasses
- `logging_streams.py` — `StreamToLogger`
- `exception_logging.py` — `install_exception_hooks`, `install_asyncio_exception_logging`

## Exports

```python
from a2a_research.backend.core.logging import (
    StreamToLogger,
    build_formatter,
    get_logger,
    log_event,
    setup_logging,
)
```
