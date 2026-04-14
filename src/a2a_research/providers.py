"""LLM provider abstraction with friendly optional-provider imports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import import_module
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from a2a_research.settings import settings

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel


@dataclass
class ModelCapabilities:
    supports_structured_output: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = True
    max_tokens: int = 4096


class LLMProvider(ABC):
    @abstractmethod
    def get_model(self) -> BaseChatModel: ...

    @abstractmethod
    def get_capabilities(self) -> ModelCapabilities: ...


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

    def get_model(self) -> BaseChatModel:
        chat_open_ai = _load_attr(
            "langchain_openai",
            "ChatOpenAI",
            "pip install langchain-openai",
        )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "api_key": self.api_key,
            "temperature": 0.3,
        }
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return cast("BaseChatModel", chat_open_ai(**kwargs))

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or settings.llm.model
        self.api_key = api_key or settings.llm.api_key

    def get_model(self) -> BaseChatModel:
        chat_anthropic = _load_attr(
            "langchain_anthropic",
            "ChatAnthropic",
            "pip install langchain-anthropic",
        )

        return cast(
            "BaseChatModel",
            chat_anthropic(
                model=self.model,
                api_key=self.api_key,
                temperature=0.3,
                max_tokens=4096,
            ),
        )

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()


class GoogleProvider(LLMProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None):
        self.model = model or settings.llm.model
        self.api_key = api_key or settings.llm.api_key

    def get_model(self) -> BaseChatModel:
        chat_google = _load_attr(
            "langchain_google_genai",
            "ChatGoogleGenerativeAI",
            "pip install langchain-google-genai",
        )

        return cast(
            "BaseChatModel",
            chat_google(
                model=self.model,
                api_key=self.api_key,
                temperature=0.3,
                max_output_tokens=4096,
            ),
        )

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(supports_function_calling=False)


class OllamaProvider(LLMProvider):
    def __init__(self, model: str | None = None, base_url: str | None = None):
        self.model = model or settings.llm.model
        self.base_url = base_url or (settings.llm.base_url or "http://localhost:11434")

    def get_model(self) -> BaseChatModel:
        chat_ollama = _load_attr(
            "langchain_ollama",
            "ChatOllama",
            "pip install langchain-ollama",
        )

        return cast(
            "BaseChatModel",
            chat_ollama(model=self.model, base_url=self.base_url, temperature=0.3),
        )

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            supports_structured_output=False,
            supports_function_calling=False,
        )


class EmbeddingProvider(ABC):
    @abstractmethod
    def get_embeddings(self) -> Any: ...


class OpenAIEmbeddings(EmbeddingProvider):
    _instance: Any = field(default=None)

    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model or settings.embedding.model
        self.api_key = api_key or settings.embedding.api_key or settings.llm.api_key
        base = base_url or settings.embedding.base_url or settings.llm.base_url
        self._base = base
        self._instance: Any = None

    def get_embeddings(self) -> Any:
        if self._instance is None:
            openai_embeddings_cls = _load_attr(
                "langchain_openai",
                "OpenAIEmbeddings",
                "pip install langchain-openai",
            )

            self._instance = openai_embeddings_cls(
                model=self.model,
                api_key=self.api_key,
                base_url=self._base if self._base else None,
            )
        return self._instance


class OllamaEmbeddings(EmbeddingProvider):
    _instance: Any = field(default=None)

    def __init__(self, base_url: str | None = None):
        self.base = base_url or settings.embedding.base_url or "http://localhost:11434"
        self._instance: Any = None

    def get_embeddings(self) -> Any:
        if self._instance is None:
            ollama_embeddings_cls = _load_attr(
                "langchain_ollama",
                "OllamaEmbeddings",
                "pip install langchain-ollama",
            )

            self._instance = ollama_embeddings_cls(base_url=self.base)
        return self._instance


_PROVIDER_MAP: dict[str, type[LLMProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
    "ollama": OllamaProvider,
}

_EMBEDDING_MAP: dict[str, type[EmbeddingProvider]] = {
    "openai": OpenAIEmbeddings,
    "ollama": OllamaEmbeddings,
}


def get_llm_provider() -> LLMProvider:
    provider_name = settings.llm.provider.lower()
    provider_class = _PROVIDER_MAP.get(provider_name)
    if provider_class is None:
        msg = f"Unknown LLM provider: {provider_name}. Supported: {list(_PROVIDER_MAP)}"
        raise ValueError(msg)
    return provider_class()


def get_embedding_provider() -> EmbeddingProvider:
    provider_name = settings.embedding.provider.lower()
    provider_class = _EMBEDDING_MAP.get(provider_name)
    if provider_class is None:
        msg = f"Unknown embedding provider: {provider_name}. Supported: {list(_EMBEDDING_MAP)}"
        raise ValueError(msg)
    return provider_class()


_llm_provider: LLMProvider | None = None
_embedding_provider: EmbeddingProvider | None = None


def get_llm() -> BaseChatModel:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _llm_provider.get_model()


def get_embedder() -> Any:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = get_embedding_provider()
    return _embedding_provider.get_embeddings()
