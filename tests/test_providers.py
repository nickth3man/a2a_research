"""Tests for src/a2a_research/providers.py — provider selection, error translation, singleton behavior."""

from __future__ import annotations

import pytest
from pydantic import BaseModel
from unittest.mock import MagicMock, patch

from a2a_research.providers import (
    AnthropicProvider,
    ChatResponse,
    GoogleProvider,
    OllamaProvider,
    OpenAIProvider,
    OpenAIEmbeddings,
    OllamaEmbeddings,
    ProviderRateLimitError,
    ProviderRequestError,
    get_embedding_provider,
    get_llm,
    get_llm_provider,
    parse_structured_response,
    reset_provider_singletons,
)


class _FakeSchema(BaseModel):
    value: str


class TestProviderSelection:
    @pytest.mark.parametrize(
        "provider_name,expected_class",
        [
            ("openai", OpenAIProvider),
            ("openrouter", OpenAIProvider),
            ("anthropic", AnthropicProvider),
            ("google", GoogleProvider),
            ("ollama", OllamaProvider),
        ],
    )
    def test_get_llm_provider_returns_correct_class(
        self, provider_name: str, expected_class: type
    ):
        with patch("a2a_research.providers.settings.llm.provider", provider_name):
            provider = get_llm_provider()
            assert isinstance(provider, expected_class)

    def test_get_llm_provider_raises_on_unknown_provider(self):
        with patch("a2a_research.providers.settings.llm.provider", "unknown"):
            with pytest.raises(ValueError, match="Unknown LLM provider"):
                get_llm_provider()


class TestEmbeddingProviderSelection:
    @pytest.mark.parametrize(
        "provider_name,expected_class",
        [
            ("openai", OpenAIEmbeddings),
            ("openrouter", OpenAIEmbeddings),
            ("ollama", OllamaEmbeddings),
        ],
    )
    def test_get_embedding_provider_returns_correct_class(
        self, provider_name: str, expected_class: type
    ):
        with patch("a2a_research.providers.settings.embedding.provider", provider_name):
            provider = get_embedding_provider()
            assert isinstance(provider, expected_class)

    def test_get_embedding_provider_raises_on_unknown_provider(self):
        with patch("a2a_research.providers.settings.embedding.provider", "unknown"):
            with pytest.raises(ValueError, match="Unknown embedding provider"):
                get_embedding_provider()


class TestSingletonBehavior:
    def test_get_llm_returns_cached_provider(self):
        reset_provider_singletons()
        with patch("a2a_research.providers.get_llm_provider") as mock_get_provider:
            mock_model = MagicMock()
            mock_provider = MagicMock()
            mock_provider.get_model.return_value = mock_model
            mock_get_provider.return_value = mock_provider

            first = get_llm()
            second = get_llm()

            mock_get_provider.assert_called_once()
            assert first is second is mock_model

    def test_reset_provider_singletons_clears_cached_providers(self):
        reset_provider_singletons()
        with patch("a2a_research.providers.get_llm_provider") as mock_get_provider:
            mock_model = MagicMock()
            mock_provider = MagicMock()
            mock_provider.get_model.return_value = mock_model
            mock_get_provider.return_value = mock_provider

            first = get_llm()
            reset_provider_singletons()
            second = get_llm()

            assert mock_get_provider.call_count == 2
            assert first is second is mock_model


class TestErrorTranslation:
    def test_openai_provider_wraps_exception_into_provider_request_error(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = Exception("openai failed")
            mock_openai = MagicMock()
            mock_openai.return_value = mock_client
            mock_load_attr.return_value = mock_openai

            provider = OpenAIProvider(model="gpt-4o", api_key="test-key")
            model = provider.get_model()
            with pytest.raises(ProviderRequestError, match="openai failed"):
                model.invoke([{"role": "user", "content": "hello"}])

    def test_anthropic_provider_wraps_exception_into_provider_request_error(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = Exception("anthropic failed")
            mock_anthropic = MagicMock()
            mock_anthropic.return_value = mock_client
            mock_load_attr.return_value = mock_anthropic

            provider = AnthropicProvider(model="claude-3", api_key="test-key")
            model = provider.get_model()
            with pytest.raises(ProviderRequestError, match="anthropic failed"):
                model.invoke([{"role": "user", "content": "hello"}])

    def test_google_provider_wraps_exception_into_provider_request_error(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.models.generate_content.side_effect = Exception("google failed")
            mock_genai = MagicMock()
            mock_genai.return_value = mock_client
            mock_load_attr.return_value = mock_genai

            provider = GoogleProvider(model="gemini", api_key="test-key")
            model = provider.get_model()
            with pytest.raises(ProviderRequestError, match="google failed"):
                model.invoke([{"role": "user", "content": "hello"}])

    def test_ollama_provider_wraps_exception_into_provider_request_error(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_ollama_chat = MagicMock()
            mock_ollama_chat.side_effect = Exception("ollama failed")
            mock_load_attr.return_value = mock_ollama_chat

            provider = OllamaProvider(model="llama3", base_url="http://localhost:11434")
            model = provider.get_model()
            with pytest.raises(ProviderRequestError, match="ollama failed"):
                model.invoke([{"role": "user", "content": "hello"}])


class TestRateLimitDetection:
    def test_429_status_code_raises_provider_rate_limit_error(self):
        class FakeException(Exception):
            status_code = 429

        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = FakeException("rate limited")
            mock_openai = MagicMock()
            mock_openai.return_value = mock_client
            mock_load_attr.return_value = mock_openai

            provider = OpenAIProvider(model="gpt-4o", api_key="test-key")
            model = provider.get_model()
            with pytest.raises(ProviderRateLimitError):
                model.invoke([{"role": "user", "content": "hello"}])

    def test_rate_limit_error_by_name_raises_provider_rate_limit_error(self):
        class RateLimitError(Exception):
            pass

        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = RateLimitError("throttled")
            mock_openai = MagicMock()
            mock_openai.return_value = mock_client
            mock_load_attr.return_value = mock_openai

            provider = OpenAIProvider(model="gpt-4o", api_key="test-key")
            model = provider.get_model()
            with pytest.raises(ProviderRateLimitError):
                model.invoke([{"role": "user", "content": "hello"}])


class TestBaseURLNormalization:
    def test_openai_provider_strips_trailing_slash(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com/"
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="hello"))]
            mock_client.chat.completions.create.return_value = response
            mock_openai = MagicMock()
            mock_openai.return_value = mock_client
            mock_load_attr.return_value = mock_openai

            provider = OpenAIProvider(
                model="gpt-4o", api_key="test-key", base_url="https://api.example.com/"
            )
            model = provider.get_model()
            result = model.invoke([{"role": "user", "content": "hi"}])
            assert isinstance(result, ChatResponse)


class TestParseStructuredResponse:
    def test_parse_structured_response_returns_none_for_invalid_json(self):
        assert parse_structured_response("not json", _FakeSchema) is None

    def test_parse_structured_response_returns_none_for_empty_string(self):
        assert parse_structured_response("", _FakeSchema) is None

    def test_parse_structured_response_uses_model_validate(self):
        class SimpleSchema(BaseModel):
            value: int

        result = parse_structured_response('{"value": 42}', SimpleSchema)
        assert result is not None
        assert result.value == 42
