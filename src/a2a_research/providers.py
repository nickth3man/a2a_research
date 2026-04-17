"""LLM and embedding provider abstraction (OpenAI-compatible HTTP, Ollama, vendor SDKs).

Raises :class:`ProviderRequestError` (and subclasses) on HTTP or configuration failures;
agents catch these to use deterministic fallbacks where appropriate.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from time import perf_counter
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from a2a_research.app_logging import get_logger
from a2a_research.settings import settings

logger = get_logger(__name__)
StructuredOutputT = TypeVar("StructuredOutputT", bound=BaseModel)

__all__ = [
    "ChatModel",
    "ChatResponse",
    "LLMProvider",
    "ModelCapabilities",
    "ProviderRateLimitError",
    "ProviderRequestError",
    "StructuredOutputT",
    "get_llm",
    "get_llm_provider",
    "parse_structured_response",
    "reset_provider_singletons",
]


class ProviderRequestError(RuntimeError):
    """Base error for upstream provider request failures."""


class ProviderRateLimitError(ProviderRequestError):
    """Transient upstream rate limit error."""


@dataclass
class ChatResponse:
    """Simple response wrapper compatible with the existing agent interface."""

    content: str


class ChatModel(ABC):
    """Abstract chat model providing a uniform invoke interface."""

    @abstractmethod
    def invoke(self, messages: list[dict[str, str]]) -> ChatResponse: ...


@dataclass
class ModelCapabilities:
    supports_structured_output: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = True
    max_tokens: int = 4096


class LLMProvider(ABC):
    @abstractmethod
    def get_model(self) -> ChatModel: ...

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities: ...


def parse_structured_response(
    content: str, schema: type[StructuredOutputT]
) -> StructuredOutputT | None:
    """Parse provider output into a Pydantic schema when valid JSON is available."""
    from a2a_research.json_utils import parse_json_safely

    data = parse_json_safely(content)
    if not data:
        return None
    try:
        return schema.model_validate(data)
    except ValidationError:
        return None


def _load_attr(module_name: str, attr_name: str, install_hint: str) -> Any:
    """Load an optional dependency attribute with a helpful error."""

    try:
        module = import_module(module_name)
    except ImportError as exc:
        msg = (
            f"Optional provider dependency '{module_name}' is not installed. "
            f"Install it with: {install_hint}"
        )
        raise ImportError(msg) from exc

    try:
        return getattr(module, attr_name)
    except AttributeError as exc:
        msg = f"Module '{module_name}' does not expose '{attr_name}'."
        raise ImportError(msg) from exc


def _base_url_to_str(value: Any) -> str:
    return str(value).rstrip("/") if value else ""


def _log_request_start(kind: str, provider: str, model: str, endpoint: str) -> float:
    logger.info(
        "Provider request start kind=%s provider=%s model=%s endpoint=%s",
        kind,
        provider,
        model,
        endpoint,
    )
    return perf_counter()


def _log_request_success(
    started_at: float, kind: str, provider: str, model: str, endpoint: str
) -> None:
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.info(
        "Provider request completed kind=%s provider=%s model=%s endpoint=%s elapsed_ms=%.1f",
        kind,
        provider,
        model,
        endpoint,
        elapsed_ms,
    )


def _log_request_failure(
    started_at: float, kind: str, provider: str, model: str, endpoint: str
) -> None:
    elapsed_ms = (perf_counter() - started_at) * 1000
    logger.exception(
        "Provider request failed kind=%s provider=%s model=%s endpoint=%s elapsed_ms=%.1f",
        kind,
        provider,
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
    exc: Exception,
    *,
    provider: str,
    model: str,
    endpoint: str,
) -> None:
    status_code = _get_exception_status_code(exc)
    exc_name = exc.__class__.__name__
    message = str(exc)
    if status_code == 429 or exc_name == "RateLimitError":
        msg = (
            f"{provider} rate limited model '{model}' at {endpoint}. "
            "Retry shortly or switch to another model/provider."
        )
        raise ProviderRateLimitError(msg) from exc

    msg = f"{provider} request failed for model '{model}' at {endpoint}: {message}"
    raise ProviderRequestError(msg) from exc


class _OpenAIChatModel(ChatModel):
    def __init__(
        self,
        model: str,
        api_key: str,
        base_url: str | None = None,
    ) -> None:
        openai = _load_attr("openai", "OpenAI", "pip install openai")
        kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai(**kwargs)
        self._model = model

    def invoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        endpoint = f"{_base_url_to_str(self._client.base_url)}/chat/completions"
        started_at = _log_request_start("chat", "openai-compatible", self._model, endpoint)
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=0.3,
            )
        except Exception as exc:
            _log_request_failure(started_at, "chat", "openai-compatible", self._model, endpoint)
            _raise_provider_error(
                exc,
                provider="OpenAI-compatible provider",
                model=self._model,
                endpoint=endpoint,
            )
        _log_request_success(started_at, "chat", "openai-compatible", self._model, endpoint)
        content = response.choices[0].message.content or ""
        return ChatResponse(content=content)


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model or settings.llm.model
        self.api_key = api_key or settings.llm.api_key
        self.base_url = base_url or settings.llm.base_url

    def get_model(self) -> ChatModel:
        return _OpenAIChatModel(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url or None,
        )

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()


class _AnthropicChatModel(ChatModel):
    def __init__(self, model: str, api_key: str) -> None:
        anthropic = _load_attr("anthropic", "Anthropic", "pip install anthropic")
        self._client = anthropic(api_key=api_key)
        self._model = model

    def invoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        system_msg = ""
        chat_messages: list[dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_msg = msg["content"]
            else:
                chat_messages.append(msg)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": chat_messages,
            "max_tokens": 4096,
            "temperature": 0.3,
        }
        if system_msg:
            kwargs["system"] = system_msg

        endpoint = "anthropic.messages.create"
        started_at = _log_request_start("chat", "anthropic", self._model, endpoint)
        try:
            response = self._client.messages.create(**kwargs)
        except Exception as exc:
            _log_request_failure(started_at, "chat", "anthropic", self._model, endpoint)
            _raise_provider_error(
                exc,
                provider="Anthropic",
                model=self._model,
                endpoint=endpoint,
            )
        _log_request_success(started_at, "chat", "anthropic", self._model, endpoint)
        text = response.content[0].text if response.content else ""
        return ChatResponse(content=text)


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or settings.llm.model
        self.api_key = api_key or settings.llm.api_key

    def get_model(self) -> ChatModel:
        return _AnthropicChatModel(model=self.model, api_key=self.api_key)

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()


class _GoogleChatModel(ChatModel):
    def __init__(self, model: str, api_key: str) -> None:
        genai = _load_attr("google.genai", "Client", "pip install google-genai")
        self._client = genai(api_key=api_key)
        self._model = model

    def invoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        contents = []
        for msg in messages:
            contents.append({"role": msg["role"], "parts": [{"text": msg["content"]}]})

        endpoint = "google.models.generate_content"
        started_at = _log_request_start("chat", "google", self._model, endpoint)
        try:
            response = self._client.models.generate_content(
                model=self._model,
                contents=contents,
            )
        except Exception as exc:
            _log_request_failure(started_at, "chat", "google", self._model, endpoint)
            _raise_provider_error(
                exc,
                provider="Google",
                model=self._model,
                endpoint=endpoint,
            )
        _log_request_success(started_at, "chat", "google", self._model, endpoint)
        return ChatResponse(content=response.text or "")


class GoogleProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or settings.llm.model
        self.api_key = api_key or settings.llm.api_key

    def get_model(self) -> ChatModel:
        return _GoogleChatModel(model=self.model, api_key=self.api_key)

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(supports_function_calling=False)


class _OllamaChatModel(ChatModel):
    def __init__(self, model: str, base_url: str) -> None:
        self._ollama = _load_attr("ollama", "chat", "pip install ollama")
        self._model = model
        self._base_url = base_url

    def invoke(self, messages: list[dict[str, str]]) -> ChatResponse:
        endpoint = f"{self._base_url.rstrip('/')}/api/chat"
        started_at = _log_request_start("chat", "ollama", self._model, endpoint)
        try:
            response = self._ollama(
                model=self._model,
                messages=messages,
                options={"temperature": 0.3},
            )
        except Exception as exc:
            _log_request_failure(started_at, "chat", "ollama", self._model, endpoint)
            _raise_provider_error(
                exc,
                provider="Ollama",
                model=self._model,
                endpoint=endpoint,
            )
        _log_request_success(started_at, "chat", "ollama", self._model, endpoint)
        return ChatResponse(content=response["message"]["content"])


class OllamaProvider(LLMProvider):
    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or settings.llm.model
        self.base_url = base_url or (settings.llm.base_url or "http://localhost:11434")

    def get_model(self) -> ChatModel:
        return _OllamaChatModel(model=self.model, base_url=self.base_url)

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_structured_output=False,
            supports_function_calling=False,
        )


_PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    # OpenRouter is OpenAI-compatible; routes to OpenAIProvider using LLM_BASE_URL
    "openrouter": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "ollama": OllamaProvider,
}


def get_llm_provider() -> LLMProvider:
    provider_name = settings.llm.provider.lower()
    provider_class = _PROVIDER_MAP.get(provider_name)
    if provider_class is None:
        msg = f"Unknown LLM provider: {provider_name}. Supported: {list(_PROVIDER_MAP)}"
        raise ValueError(msg)
    return provider_class()


_llm_provider: LLMProvider | None = None


def get_llm() -> ChatModel:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _llm_provider.get_model()


def reset_provider_singletons() -> None:
    global _llm_provider
    _llm_provider = None
