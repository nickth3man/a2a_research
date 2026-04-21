"""Tests for OpenRouterChatModel."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

import a2a_research.providers as providers_module
from a2a_research.providers import (
    ChatResponse,
    OpenRouterChatModel,
    ProviderRateLimitError,
    ProviderRequestError,
)


def _response_with(content: str | None) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock(message=MagicMock(content=content))]
    return response


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
