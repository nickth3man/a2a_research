"""Helpers for OpenRouter chat requests (logging, parsing, errors)."""

from __future__ import annotations

from time import perf_counter
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.llm.protocol import ChatResponse
from a2a_research.backend.llm.providers_errors import (
    ProviderRateLimitError,
    ProviderRequestError,
)

logger = get_logger(__name__)
StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)

__all__ = [
    "StructuredOutputT",
    "_base_url_to_str",
    "_get_exception_status_code",
    "_log_request_failure",
    "_log_request_start",
    "_log_request_success",
    "_raise_provider_error",
    "build_chat_response_from_openai",
    "parse_structured_response",
]


def parse_structured_response(
    content: str, schema: type[StructuredOutputT]
) -> StructuredOutputT | None:
    """Parse provider output into a Pydantic schema when valid JSON is"""
    """available."""
    from a2a_research.backend.core.utils.json_utils import parse_json_safely

    data = parse_json_safely(content)
    if not data:
        return None
    try:
        return schema.model_validate(data)
    except ValidationError:
        return None


def _base_url_to_str(value: Any) -> str:
    return str(value).rstrip("/") if value else ""


def _log_request_start(kind: str, model: str, endpoint: str) -> float:
    logger.info(
        "Provider request start kind=%s provider=%s model=%s endpoint=%s",
        kind,
        "openrouter",
        model,
        endpoint,
    )
    return perf_counter()


def _log_request_success(
    started_at: float, kind: str, model: str, endpoint: str
) -> None:
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Provider request completed kind=%s provider=%s"
        " model=%s endpoint=%s elapsed_ms=%.1f",
        kind,
        "openrouter",
        model,
        endpoint,
        elapsed_ms,
    )


def _log_request_failure(
    started_at: float, kind: str, model: str, endpoint: str
) -> None:
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.exception(
        "Provider request failed kind=%s provider=%s"
        " model=%s endpoint=%s elapsed_ms=%.1f",
        kind,
        "openrouter",
        model,
        endpoint,
        elapsed_ms,
    )


def _get_exception_status_code(exc: Exception) -> int | None:
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _raise_provider_error(
    exc: Exception, *, model: str, endpoint: str
) -> None:
    status_code = _get_exception_status_code(exc)
    exc_name = exc.__class__.__name__
    message = str(exc)
    if status_code == 429 or exc_name == "RateLimitError":
        msg = (
            f"OpenRouter rate limited model '{model}' at {endpoint}. "
            "Retry shortly or switch models."
        )
        raise ProviderRateLimitError(msg) from exc

    msg = (
        f"OpenRouter request failed for model '{model}' at "
        f"{endpoint}: {message}"
    )
    raise ProviderRequestError(msg) from exc


def build_chat_response_from_openai(response: Any, model: str) -> ChatResponse:
    """Map an OpenAI-compatible completion response to ChatResponse."""
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
    completion_tokens = (
        getattr(usage, "completion_tokens", None) if usage else None
    )
    finish_reason = (
        getattr(response.choices[0], "finish_reason", "")
        if response.choices
        else ""
    )
    return ChatResponse(
        content=content,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        finish_reason=finish_reason,
        model=model,
    )
