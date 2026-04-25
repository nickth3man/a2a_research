"""OpenRouter-backed async chat model used across the research pipeline."""

from __future__ import annotations

from typing import Any, cast

import logfire
from openai import AsyncOpenAI

from core import settings
from llm.protocol import ChatModelProtocol, ChatResponse
from llm.providers_errors import (
    ProviderRateLimitError,
    ProviderRequestError,
)
from llm.providers_support import (
    StructuredOutputT,
    _base_url_to_str,
    _log_request_failure,
    _log_request_start,
    _log_request_success,
    _raise_provider_error,
    build_chat_response_from_openai,
    parse_structured_response,
)

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
                _raise_provider_error(
                    exc, model=self._model, endpoint=endpoint
                )
        _log_request_success(started_at, "chat", self._model, endpoint)
        if response is None:
            msg = "Provider returned no response."
            raise ProviderRequestError(msg)
        return build_chat_response_from_openai(response, self._model)


_llm: ChatModelProtocol | None = None


def get_llm() -> ChatModelProtocol:
    global _llm
    if _llm is None:
        _llm = OpenRouterChatModel()
    return _llm


def reset_provider_singletons() -> None:
    global _llm
    _llm = None
