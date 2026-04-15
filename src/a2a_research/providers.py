"""LLM provider abstraction with friendly optional-provider imports."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from importlib import import_module
from typing import Any, cast

from a2a_research.settings import settings


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
        response = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=0.3,
        )
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

        response = self._client.messages.create(**kwargs)
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

        response = self._client.models.generate_content(
            model=self._model,
            contents=contents,
        )
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
        response = self._ollama(
            model=self._model,
            messages=messages,
            options={"temperature": 0.3},
        )
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


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...


class OpenAIEmbeddings(EmbeddingProvider):
    def __init__(
        self,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model or settings.embedding.model
        self.api_key = api_key or settings.embedding.api_key or settings.llm.api_key
        base = base_url or settings.embedding.base_url or settings.llm.base_url
        self._base_url = base

        openai = _load_attr("openai", "OpenAI", "pip install openai")
        kwargs: dict[str, Any] = {"api_key": self.api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = openai(**kwargs)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(input=texts, model=self.model)
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self._client.embeddings.create(input=[text], model=self.model)
        return cast("list[float]", response.data[0].embedding)


class OllamaEmbeddings(EmbeddingProvider):
    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.model = model or settings.embedding.model
        self.base_url = base_url or settings.embedding.base_url or "http://localhost:11434"
        self._embeddings = _load_attr("ollama", "embeddings", "pip install ollama")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            cast("list[float]", self._embeddings(model=self.model, prompt=text)["embedding"])
            for text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        return cast("list[float]", self._embeddings(model=self.model, prompt=text)["embedding"])


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


def get_llm() -> ChatModel:
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = get_llm_provider()
    return _llm_provider.get_model()


def get_embedder() -> EmbeddingProvider:
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = get_embedding_provider()
    return _embedding_provider
