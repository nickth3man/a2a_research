"""Shared logging setup and logger factory.

``setup_logging`` applies :mod:`logging` ``basicConfig`` once, using
``AppSettings.log_level``. ``get_logger`` ensures setup has run before returning
a named logger.
"""

from __future__ import annotations

import logging

from a2a_research.settings import settings

_CONFIGURED = False


def setup_logging() -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return

    level_name = settings.log_level.upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
