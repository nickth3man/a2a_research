"""OpenRouter-backed async chat model used across the research pipeline."""

from __future__ import annotations

from time import perf_counter
import logfire
from typing import Any, TypeVar, cast

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from a2a_research.backend.core.logging.app_logging import get_logger
from a2a_research.backend.core.settings import settings
from a2a_research.backend.llm.protocol import ChatModelProtocol, ChatResponse
logger = get_logger(__name__)
StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)

__all__ = [
    "ChatResponse",
    "OpenRouterChatModel",
    "ProviderRateLimitError",
    "ProviderRequestError",
    "StructuredOutputT",
    "get_llm",
    "parse_structured_response",
    "reset_provider_singletons",
]


class ProviderRequestError(RuntimeError):
    """Base error for upstream provider request failures."""


class ProviderRateLimitError(ProviderRequestError):
    """Transient upstream rate limit error."""



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


class OpenRouterChatModel:
    """Async OpenAI-compatible chat client pinned to OpenRouter settings."""

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._model = model or settings.llm.model
        self._api_key = settings.llm.api_key if api_key is None else api_key
        self._base_url = (
            settings.llm.base_url if base_url is None else base_url
        )
        self._client: AsyncOpenAI | None = None

    def _get_client(self) -> AsyncOpenAI:
        if not self._api_key:
            msg = "LLM_API_KEY is required for OpenRouter requests."
            raise ProviderRequestError(msg)
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=self._api_key, base_url=self._base_url
            )
        return self._client

    async def ainvoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        client = self._get_client()
        endpoint = f"{_base_url_to_str(self._base_url)}/chat/completions"
        started_at = _log_request_start("chat", self._model, endpoint)
        response: Any = None
        with logfire.span(
            "llm.invoke",
            gen_ai_system="openrouter",
            gen_ai_operation="chat",
            gen_ai_request_model=self._model,
            gen_ai_request_temperature=0.3,
        ):
            try:
                response = await client.chat.completions.create(
                    model=self._model,
                    messages=cast("Any", messages),
                    temperature=0.3,
                )
            except Exception as exc:
                _log_request_failure(started_at, "chat", self._model, endpoint)
                _raise_provider_error(exc, model=self._model, endpoint=endpoint)

        _log_request_success(started_at, "chat", self._model, endpoint)
        if response is None:
            msg = "Provider returned no response."
            raise ProviderRequestError(msg)
        content = response.choices[0].message.content or ""
        usage = getattr(response, "usage", None)
        prompt_tokens = (
            getattr(usage, "prompt_tokens", None) if usage else None
        )
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
            model=self._model,
        )


_llm: ChatModelProtocol | None = None


def get_llm() -> ChatModelProtocol:
    global _llm
    if _llm is None:
        _llm = OpenRouterChatModel()
    return _llm


def reset_provider_singletons() -> None:
    global _llm
    _llm = None
