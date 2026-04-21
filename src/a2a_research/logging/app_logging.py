"""Shared logging setup and logger factory.

``setup_logging`` configures the root logger once. The same ``LOG_LEVEL``
applies everywhere: console and every log file. Records are never dropped by
level within the app.

Files under ``logs/``:

- ``everything.log`` — full audit trail (all loggers).
- ``app.log`` — ``a2a_research.*`` only (this package).
- ``a2a_sdk.log`` — third-party ``a2a`` SDK (``a2a.*``, not ``a2a_research``).
- ``http_clients.log`` — ``httpx`` / ``httpcore``.
- ``mesop_server.log`` — Mesop, Flask, Werkzeug, Uvicorn.
- ``stdio.log`` — captured ``stdout`` / ``stderr`` when using
  :func:`redirect_stdio_to_logging`.
- ``warnings.log`` — Python :mod:`warnings` (``py.warnings``).
"""

from __future__ import annotations

import asyncio
import logging
import sys
import threading
from pathlib import Path
from typing import Any

from .logging_formatters import (
    A2aSdkFilter,
    HttpClientsFilter,
    MesopServerFilter,
    PrefixFilter,
    WarningsFilter,
    build_formatter,
    log_event,
)
from .logging_streams import StreamToLogger
from a2a_research.settings import settings

_CONFIGURED = False
_LOG_DIR = Path.cwd() / "logs"
_LOG_EVERYTHING = _LOG_DIR / "everything.log"
_APP_LOG = _LOG_DIR / "app.log"
_LOG_A2A_SDK = _LOG_DIR / "a2a_sdk.log"
_LOG_HTTP_CLIENTS = _LOG_DIR / "http_clients.log"
_LOG_MESOP_SERVER = _LOG_DIR / "mesop_server.log"
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


def _install_exception_hooks() -> None:
    """Install exception hooks that log and preserve original handlers."""
    original_excepthook = sys.excepthook
    original_thread_excepthook = threading.excepthook

    def _log_unhandled_exception(
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: Any,
    ) -> None:
        if exc_type is not None and exc_value is not None:
            if not issubclass(exc_type, KeyboardInterrupt):
                logging.getLogger("a2a_research.unhandled").error(
                    "Unhandled exception",
                    exc_info=(exc_type, exc_value, exc_traceback),
                )
        original_excepthook(exc_type, exc_value, exc_traceback)

    def _log_thread_exception(args: threading.ExceptHookArgs) -> None:
        if args.exc_type is not None and args.exc_value is not None:
            logging.getLogger("a2a_research.threading").error(
                "Unhandled thread exception in %s",
                getattr(args.thread, "name", "<unknown>"),
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
        else:
            logging.getLogger("a2a_research.threading").error(
                "Unhandled thread exception in %s (no exception info)",
                getattr(args.thread, "name", "<unknown>"),
            )
        original_thread_excepthook(args)

    sys.excepthook = _log_unhandled_exception
    threading.excepthook = _log_thread_exception


def install_asyncio_exception_logging(
    loop: asyncio.AbstractEventLoop | None = None,
) -> None:
    """Attach an exception handler that records background task failures."""
    setup_logging()
    target_loop = loop
    if target_loop is None:
        try:
            target_loop = asyncio.get_running_loop()
        except RuntimeError:
            return

    def _handle_async_exception(
        loop: asyncio.AbstractEventLoop, context: dict[str, object]
    ) -> None:
        exc_raw = context.get("exception")
        exc_info: BaseException | None = (
            exc_raw if isinstance(exc_raw, BaseException) else None
        )
        logging.getLogger("a2a_research.asyncio").error(
            "Asyncio exception: %s",
            context.get("message", "no message"),
            extra={"context_keys": sorted(context.keys())},
            exc_info=exc_info,
        )
        default_handler = loop.default_exception_handler
        default_handler(context)

    target_loop.set_exception_handler(_handle_async_exception)


def _file_handler(
    path: Path, level: int, formatter: logging.Formatter
) -> logging.FileHandler:
    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setLevel(level)
    handler.setFormatter(formatter)
    return handler


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
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

    mesop_handler = _file_handler(_LOG_MESOP_SERVER, level, formatter)
    mesop_handler.addFilter(MesopServerFilter())

    warnings_handler = _file_handler(_LOG_WARNINGS, level, formatter)
    warnings_handler.addFilter(WarningsFilter())

    root.addHandler(console_handler)
    root.addHandler(everything_handler)
    root.addHandler(app_handler)
    root.addHandler(a2a_sdk_handler)
    root.addHandler(http_handler)
    root.addHandler(mesop_handler)
    root.addHandler(warnings_handler)

    logging.captureWarnings(True)
    _configure_named_logger("asyncio", level)
    _configure_named_logger("mesop", level)
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
    _install_exception_hooks()

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
            "mesop_server": str(_LOG_MESOP_SERVER),
            "stdio": str(_LOG_STDIO),
            "warnings": str(_LOG_WARNINGS),
        },
    )
    _CONFIGURED = True


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
    "install_asyncio_exception_logging",
    "log_event",
    "redirect_stdio_to_logging",
    "setup_logging",
]


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
