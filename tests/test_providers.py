"""Tests for src/a2a_research/providers.py — OpenRouter-only async behavior."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import BaseModel

import a2a_research.providers as providers_module
from a2a_research.providers import (
    ChatResponse,
    OpenRouterChatModel,
    ProviderRateLimitError,
    ProviderRequestError,
    get_llm,
    parse_structured_response,
    reset_provider_singletons,
)


class _FakeSchema(BaseModel):
    value: str


def _response_with(content: str | None) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


class TestSingletonBehavior:
    def test_get_llm_returns_cached_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reset_provider_singletons()
        created: list[object] = []

        class FakeModel:
            def __init__(self) -> None:
                created.append(self)

        monkeypatch.setattr(providers_module, "OpenRouterChatModel", FakeModel)

        first = get_llm()
        second = get_llm()

        assert first is second
        assert len(created) == 1

    def test_reset_provider_singletons_clears_cached_model(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reset_provider_singletons()
        created: list[object] = []

        class FakeModel:
            def __init__(self) -> None:
                created.append(self)

        monkeypatch.setattr(providers_module, "OpenRouterChatModel", FakeModel)

        first = get_llm()
        reset_provider_singletons()
        second = get_llm()

        assert first is not second
        assert len(created) == 2


class TestOpenRouterChatModel:
    @pytest.mark.asyncio
    async def test_ainvoke_returns_chatresponse_with_assistant_content(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_response_with("hi there")
        )
        monkeypatch.setattr(
            providers_module,
            "AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        model = OpenRouterChatModel(
            model="openrouter/test-model",
            api_key="test-key",
            base_url="https://openrouter.example/v1",
        )
        result = await model.ainvoke([{"role": "user", "content": "ping"}])

        assert isinstance(result, ChatResponse)
        assert result.content == "hi there"
        mock_client.chat.completions.create.assert_awaited_once()
        assert (
            mock_client.chat.completions.create.call_args.kwargs["model"]
            == "openrouter/test-model"
        )

    @pytest.mark.asyncio
    async def test_ainvoke_replaces_none_content_with_empty_string(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            return_value=_response_with(None)
        )
        monkeypatch.setattr(
            providers_module,
            "AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        model = OpenRouterChatModel(api_key="test-key")
        result = await model.ainvoke([{"role": "user", "content": "ping"}])

        assert result.content == ""

    @pytest.mark.asyncio
    async def test_ainvoke_requires_api_key_on_first_use(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async_openai = MagicMock()
        monkeypatch.setattr(providers_module, "AsyncOpenAI", async_openai)

        model = OpenRouterChatModel(api_key="")
        with pytest.raises(ProviderRequestError, match="LLM_API_KEY"):
            await model.ainvoke([{"role": "user", "content": "ping"}])

        async_openai.assert_not_called()

    @pytest.mark.asyncio
    async def test_openrouter_wraps_exception_into_provider_request_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("openrouter failed")
        )
        monkeypatch.setattr(
            providers_module,
            "AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        model = OpenRouterChatModel(model="gpt-4o", api_key="test-key")
        with pytest.raises(ProviderRequestError, match="openrouter failed"):
            await model.ainvoke([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_429_status_code_raises_provider_rate_limit_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class FakeError(Exception):
            status_code = 429

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=FakeError("rate limited")
        )
        monkeypatch.setattr(
            providers_module,
            "AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        model = OpenRouterChatModel(model="gpt-4o", api_key="test-key")
        with pytest.raises(ProviderRateLimitError):
            await model.ainvoke([{"role": "user", "content": "hello"}])

    @pytest.mark.asyncio
    async def test_rate_limit_error_by_name_raises_provider_rate_limit_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class RateLimitError(Exception):
            pass

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(
            side_effect=RateLimitError("throttled")
        )
        monkeypatch.setattr(
            providers_module,
            "AsyncOpenAI",
            MagicMock(return_value=mock_client),
        )

        model = OpenRouterChatModel(model="gpt-4o", api_key="test-key")
        with pytest.raises(ProviderRateLimitError):
            await model.ainvoke([{"role": "user", "content": "hello"}])


class TestParseStructuredResponse:
    def test_parse_structured_response_returns_none_for_invalid_json(
        self,
    ) -> None:
        assert parse_structured_response("not json", _FakeSchema) is None

    def test_parse_structured_response_returns_none_for_empty_string(
        self,
    ) -> None:
        assert parse_structured_response("", _FakeSchema) is None

    def test_parse_structured_response_returns_none_for_json_that_fails_schema(
        self,
    ) -> None:
        class StrictSchema(BaseModel):
            value: int

        assert (
            parse_structured_response('{"value": "not-an-int"}', StrictSchema)
            is None
        )

    def test_parse_structured_response_uses_model_validate(self) -> None:
        class SimpleSchema(BaseModel):
            value: int

        result = parse_structured_response('{"value": 42}', SimpleSchema)
        assert result is not None
        assert result.value == 42
