"""Shared logging setup and logger factory.

``setup_logging`` configures the root logger once. The same ``LOG_LEVEL``
applies everywhere: console and every log file. Records are never dropped by
level within the app.

Files under ``logs/``:

- ``everything.log`` — full audit trail (all loggers).
- ``app.log`` — ``a2a_research.*`` only (this package).
- ``a2a_sdk.log`` — third-party ``a2a`` SDK (``a2a.*``, not ``a2a_research``).
- ``http_clients.log`` — ``httpx`` / ``httpcore``.
- ``server_runtime.log`` — Flask, Werkzeug, Uvicorn.
- ``stdio.log`` — captured ``stdout`` / ``stderr`` when using
  :func:`redirect_stdio_to_logging`.
- ``warnings.log`` — Python :mod:`warnings` (``py.warnings``).
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from core.settings import settings

from .exception_logging import install_exception_hooks
from .logging_formatters import (
    A2aSdkFilter,
    HttpClientsFilter,
    PrefixFilter,
    ServerRuntimeFilter,
    WarningsFilter,
    build_formatter,
    log_event,
)
from .logging_streams import StreamToLogger

_configured = False
_LOG_DIR = Path.cwd() / "logs"
_LOG_EVERYTHING = _LOG_DIR / "everything.log"
_APP_LOG = _LOG_DIR / "app.log"
_LOG_A2A_SDK = _LOG_DIR / "a2a_sdk.log"
_LOG_HTTP_CLIENTS = _LOG_DIR / "http_clients.log"
_LOG_SERVER_RUNTIME = _LOG_DIR / "server_runtime.log"
_LOG_STDIO = _LOG_DIR / "stdio.log"
_LOG_WARNINGS = _LOG_DIR / "warnings.log"
_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr


def _configure_named_logger(
    name: str, level: int, propagate: bool = True
) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = propagate
    return logger


def _file_handler(
    path: Path, level: int, formatter: logging.Formatter
) -> logging.FileHandler:
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging() -> None:
    global _configured
    if _configured:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.DEBUG)
    formatter = build_formatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    everything_handler = _file_handler(_LOG_EVERYTHING, level, formatter)

    app_handler = _file_handler(_APP_LOG, level, formatter)
    app_handler.addFilter(PrefixFilter(("a2a_research",)))
    a2a_sdk_handler = _file_handler(_LOG_A2A_SDK, level, formatter)
    a2a_sdk_handler.addFilter(A2aSdkFilter())
    http_handler = _file_handler(_LOG_HTTP_CLIENTS, level, formatter)
    http_handler.addFilter(HttpClientsFilter())
    server_runtime_handler = _file_handler(
        _LOG_SERVER_RUNTIME, level, formatter
    )
    server_runtime_handler.addFilter(ServerRuntimeFilter())
    warnings_handler = _file_handler(_LOG_WARNINGS, level, formatter)
    warnings_handler.addFilter(WarningsFilter())

    handlers: list[logging.Handler] = [
        console_handler,
        everything_handler,
        app_handler,
        a2a_sdk_handler,
        http_handler,
        server_runtime_handler,
        warnings_handler,
    ]
    for h in handlers:
        root.addHandler(h)

    logging.captureWarnings(True)
    _configure_named_logger("asyncio", level)
    _configure_named_logger("werkzeug", level)
    _configure_named_logger("flask", level)
    logging.getLogger("trafilatura.downloads").setLevel(logging.CRITICAL)
    logging.getLogger("trafilatura.core").setLevel(logging.ERROR)
    stderr_logger = _configure_named_logger("stderr", level, propagate=False)
    stdout_logger = _configure_named_logger("stdout", level, propagate=False)
    stderr_logger.handlers.clear()
    stdout_logger.handlers.clear()
    stdio_handler = _file_handler(_LOG_STDIO, level, formatter)
    for h in (everything_handler, stdio_handler):
        stdout_logger.addHandler(h)
        stderr_logger.addHandler(h)
    install_exception_hooks()

    log_event(
        logging.getLogger(__name__),
        logging.INFO,
        "logging.configured",
        configured_level=level_name,
        log_files={
            "everything": str(_LOG_EVERYTHING),
            "app": str(_APP_LOG),
            "a2a_sdk": str(_LOG_A2A_SDK),
            "http_clients": str(_LOG_HTTP_CLIENTS),
            "server_runtime": str(_LOG_SERVER_RUNTIME),
            "stdio": str(_LOG_STDIO),
            "warnings": str(_LOG_WARNINGS),
        },
    )
    _configured = True


def redirect_stdio_to_logging() -> None:
    """Opt-in redirection of sys.stdout/stderr to the logging system."""
    setup_logging()
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.DEBUG)
    sys.stdout = StreamToLogger(
        logging.getLogger("stdout"), level, _ORIGINAL_STDOUT
    )
    sys.stderr = StreamToLogger(
        logging.getLogger("stderr"), level, _ORIGINAL_STDERR
    )


__all__ = [
    "get_logger",
    "log_event",
    "redirect_stdio_to_logging",
    "setup_logging",
]


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
