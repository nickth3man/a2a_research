"""LLM call wrapper shared by all PocketFlow agents.

Kept as a module-level function accessed through the module object so tests can
patch :func:`call_llm` once at this location and have the mock take effect in
every agent module.
"""

from __future__ import annotations

from time import perf_counter

from a2a_research.app_logging import get_logger
from a2a_research.providers import get_llm

logger = get_logger(__name__)


def call_llm(system_prompt: str, user_content: str, *, stage: str) -> str:
    """Invoke the configured LLM and return the response ``content`` string."""
    logger.info(
        "LLM stage=%s start system_chars=%s user_chars=%s",
        stage,
        len(system_prompt),
        len(user_content),
    )
    started_at = perf_counter()
    llm = get_llm()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
    try:
        response = llm.invoke(messages)
    except Exception:
        elapsed_ms = (perf_counter() - started_at) * 1000
        logger.exception("LLM stage=%s failed elapsed_ms=%.1f", stage, elapsed_ms)
        raise
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info("LLM stage=%s completed elapsed_ms=%.1f", stage, elapsed_ms)
    return (response.content or "") if hasattr(response, "content") else str(response)
