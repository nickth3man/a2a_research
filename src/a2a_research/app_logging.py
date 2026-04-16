"""Shared logging setup and logger factory.

``setup_logging`` applies :mod:`logging` ``basicConfig`` once, using
``AppSettings.log_level``. ``get_logger`` ensures setup has run before returning
a named logger.
"""

from __future__ import annotations

import asyncio
import itertools
import json
import logging
import os
import sys
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from a2a_research.settings import settings

if TYPE_CHECKING:
    from types import TracebackType

_CONFIGURED = False
_LOG_DIR = Path.cwd() / "logs"
_APP_LOG = _LOG_DIR / "app.log"
_ERROR_LOG = _LOG_DIR / "errors.log"
_TRACE_LOG = _LOG_DIR / "trace.log"
_ORIGINAL_STDOUT = sys.stdout
_ORIGINAL_STDERR = sys.stderr
_EVENT_COUNTER = itertools.count(1)


class _StreamToLogger:
    """Mirror writes into the logging system while preserving terminal output."""

    def __init__(self, logger: logging.Logger, level: int, original_stream: TextIO) -> None:
        self._logger = logger
        self._level = level
        self._original_stream = original_stream

    def write(self, message: str) -> None:
        self._original_stream.write(message)
        text = message.strip()
        if text:
            self._logger.log(self._level, text)

    def flush(self) -> None:
        self._original_stream.flush()

    def isatty(self) -> bool:
        return bool(getattr(self._original_stream, "isatty", lambda: False)())


def _build_formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] pid=%(process)d tid=%(thread)d %(message)s"
    )


def _normalize_log_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _normalize_log_value(val) for key, val in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_log_value(item) for item in value]
    if hasattr(value, "value"):
        return _normalize_log_value(value.value)
    if hasattr(value, "model_dump"):
        return _normalize_log_value(value.model_dump())
    if hasattr(value, "__dict__"):
        return _normalize_log_value(vars(value))
    return repr(value)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    """Write a granular structured event log line."""
    payload = {
        "seq": next(_EVENT_COUNTER),
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        **{key: _normalize_log_value(value) for key, value in fields.items()},
    }
    logger.log(level, "event=%s payload=%s", event, json.dumps(payload, sort_keys=True))


def _configure_named_logger(name: str, level: int, propagate: bool = True) -> logging.Logger:
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
        exc_traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None and exc_value is not None and not issubclass(exc_type, KeyboardInterrupt):
            logging.getLogger("a2a_research.unhandled").error(
                "Unhandled exception",
                exc_info=(exc_type, exc_value, exc_traceback),
            )
        original_excepthook(exc_type, exc_value, exc_traceback)  # type: ignore[arg-type]

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


def install_asyncio_exception_logging(loop: asyncio.AbstractEventLoop | None = None) -> None:
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
        exc_info: BaseException | None = exc_raw if isinstance(exc_raw, BaseException) else None
        logging.getLogger("a2a_research.asyncio").error(
            "Asyncio exception: %s",
            context.get("message", "no message"),
            extra={"context_keys": sorted(context.keys())},
            exc_info=exc_info,
        )
        default_handler = loop.default_exception_handler
        default_handler(context)

    target_loop.set_exception_handler(_handle_async_exception)


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    formatter = _build_formatter()

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()

    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)

    app_file_handler = logging.FileHandler(_APP_LOG, encoding="utf-8")
    app_file_handler.setLevel(level)
    app_file_handler.setFormatter(formatter)

    error_file_handler = logging.FileHandler(_ERROR_LOG, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(formatter)

    trace_file_handler = logging.FileHandler(_TRACE_LOG, encoding="utf-8")
    trace_file_handler.setLevel(logging.DEBUG)
    trace_file_handler.setFormatter(formatter)

    root.addHandler(console_handler)
    root.addHandler(app_file_handler)
    root.addHandler(error_file_handler)
    root.addHandler(trace_file_handler)

    logging.captureWarnings(True)
    _configure_named_logger("asyncio", level)
    _configure_named_logger("mesop", level)
    _configure_named_logger("werkzeug", level)
    _configure_named_logger("flask", level)
    # stdout/stderr loggers: disable propagation to avoid duplicate console output
    # (they write directly to terminal via _StreamToLogger._original_stream)
    stderr_logger = _configure_named_logger("stderr", logging.ERROR, propagate=False)
    stdout_logger = _configure_named_logger("stdout", level, propagate=False)
    # Attach file handlers directly to prevent log loss when propagation is off
    for handler in [app_file_handler, error_file_handler, trace_file_handler]:
        stdout_logger.addHandler(handler)
        stderr_logger.addHandler(handler)
    _install_exception_hooks()

    log_event(
        logging.getLogger(__name__),
        logging.INFO,
        "logging.configured",
        configured_level=level_name,
        app_log=_APP_LOG,
        error_log=_ERROR_LOG,
        trace_log=_TRACE_LOG,
    )
    _CONFIGURED = True


def redirect_stdio_to_logging() -> None:
    """Opt-in redirection of sys.stdout/stderr to the logging system."""
    sys.stdout = _StreamToLogger(logging.getLogger("stdout"), logging.INFO, _ORIGINAL_STDOUT)
    sys.stderr = _StreamToLogger(logging.getLogger("stderr"), logging.ERROR, _ORIGINAL_STDERR)


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
