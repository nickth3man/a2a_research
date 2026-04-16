"""Tests for src/a2a_research/providers.py — provider selection, error translation, singleton behavior."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from a2a_research.providers import (
    AnthropicProvider,
    ChatResponse,
    GoogleProvider,
    OllamaEmbeddings,
    OllamaProvider,
    OpenAIEmbeddings,
    OpenAIProvider,
    ProviderRateLimitError,
    ProviderRequestError,
    get_embedder,
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
        with (
            patch("a2a_research.providers.settings.llm.provider", "unknown"),
            pytest.raises(ValueError, match="Unknown LLM provider"),
        ):
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
        with (
            patch("a2a_research.providers.settings.embedding.provider", "unknown"),
            pytest.raises(ValueError, match="Unknown embedding provider"),
        ):
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

    def test_get_embedder_caches_provider_between_calls(self):
        """Repeated calls must return the same embedder instance; dropping this cache
        would re-instantiate the SDK client (and its HTTP session) on every retrieval."""
        reset_provider_singletons()
        with patch("a2a_research.providers.get_embedding_provider") as mock_get:
            mock_get.return_value = MagicMock()
            first = get_embedder()
            second = get_embedder()
        assert first is second
        mock_get.assert_called_once()


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
        class FakeError(Exception):
            status_code = 429

        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.chat.completions.create.side_effect = FakeError("rate limited")
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

    def test_parse_structured_response_returns_none_for_json_that_fails_schema(self):
        """Valid JSON that does not match the schema must return None, not raise."""

        class StrictSchema(BaseModel):
            value: int

        assert parse_structured_response('{"value": "not-an-int"}', StrictSchema) is None

    def test_parse_structured_response_uses_model_validate(self):
        class SimpleSchema(BaseModel):
            value: int

        result = parse_structured_response('{"value": 42}', SimpleSchema)
        assert result is not None
        assert result.value == 42


class TestOpenAIChatSuccessPath:
    def test_invoke_returns_chatresponse_with_assistant_content(self):
        """Success path must unwrap the OpenAI response into a plain ``ChatResponse``
        carrying ``choices[0].message.content``."""
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com"
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content="hi there"))]
            mock_client.chat.completions.create.return_value = response
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            provider = OpenAIProvider(model="gpt-4o", api_key="k", base_url="https://e.com")
            result = provider.get_model().invoke([{"role": "user", "content": "ping"}])

        assert isinstance(result, ChatResponse)
        assert result.content == "hi there"
        mock_client.chat.completions.create.assert_called_once()
        assert mock_client.chat.completions.create.call_args.kwargs["model"] == "gpt-4o"

    def test_invoke_replaces_none_content_with_empty_string(self):
        """Some OpenAI-compatible backends return ``content=None``; the wrapper must
        coerce that to ``""`` so downstream JSON parsing does not crash."""
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com"
            response = MagicMock()
            response.choices = [MagicMock(message=MagicMock(content=None))]
            mock_client.chat.completions.create.return_value = response
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            provider = OpenAIProvider(model="m", api_key="k")
            result = provider.get_model().invoke([{"role": "user", "content": "ping"}])

        assert result.content == ""


class TestAnthropicChatMessageShaping:
    def test_system_message_is_extracted_and_chat_messages_are_user_only(self):
        """Anthropic's API takes ``system`` as a kwarg; the adapter must peel the system
        message out of the messages array and pass the remainder as-is."""
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            response = MagicMock()
            response.content = [MagicMock(text="answer")]
            mock_client.messages.create.return_value = response
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            provider = AnthropicProvider(model="claude-3", api_key="k")
            result = provider.get_model().invoke(
                [
                    {"role": "system", "content": "You are a helper."},
                    {"role": "user", "content": "ping"},
                ]
            )

        kwargs = mock_client.messages.create.call_args.kwargs
        assert kwargs["system"] == "You are a helper."
        assert kwargs["messages"] == [{"role": "user", "content": "ping"}]
        assert result.content == "answer"

    def test_empty_content_array_returns_empty_string(self):
        """If Anthropic returns an empty ``content`` array the wrapper must return
        an empty ``ChatResponse`` instead of raising IndexError."""
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            response = MagicMock()
            response.content = []
            mock_client.messages.create.return_value = response
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            provider = AnthropicProvider(model="claude-3", api_key="k")
            result = provider.get_model().invoke([{"role": "user", "content": "ping"}])

        assert result.content == ""


class TestOpenAIEmbeddingsSuccessPath:
    def test_embed_documents_returns_vectors_in_order(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com"
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=[0.1, 0.2]), MagicMock(embedding=[0.3, 0.4])]
            )
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            embedder = OpenAIEmbeddings(model="emb", api_key="k", base_url="https://e.com")
            out = embedder.embed_documents(["doc one", "doc two"])

        assert out == [[0.1, 0.2], [0.3, 0.4]]
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["input"] == ["doc one", "doc two"]
        assert call_kwargs["model"] == "emb"

    def test_embed_query_returns_single_vector(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com"
            mock_client.embeddings.create.return_value = MagicMock(
                data=[MagicMock(embedding=[0.5, 0.6, 0.7])]
            )
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            embedder = OpenAIEmbeddings(model="emb", api_key="k")
            out = embedder.embed_query("q")

        assert out == [0.5, 0.6, 0.7]
        call_kwargs = mock_client.embeddings.create.call_args.kwargs
        assert call_kwargs["input"] == ["q"]

    def test_embed_query_wraps_provider_error(self):
        with patch("a2a_research.providers._load_attr") as mock_load_attr:
            mock_client = MagicMock()
            mock_client.base_url = "https://api.example.com"
            mock_client.embeddings.create.side_effect = Exception("boom")
            mock_load_attr.return_value = MagicMock(return_value=mock_client)

            embedder = OpenAIEmbeddings(model="emb", api_key="k")
            with pytest.raises(ProviderRequestError, match="boom"):
                embedder.embed_query("q")


class TestLoadAttrErrorMessages:
    def test_missing_module_raises_import_error_with_install_hint(self):
        from a2a_research.providers import _load_attr

        with pytest.raises(ImportError, match="pip install totally_fake"):
            _load_attr(
                "a2a_research_totally_fake_module_xyz",
                "X",
                "pip install totally_fake",
            )
