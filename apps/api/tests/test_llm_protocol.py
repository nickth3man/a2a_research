"""Tests for LLM protocol, TestChatModel, and factory."""

from __future__ import annotations

import pytest

from a2a_research.backend.llm.factory import create_chat_model
from a2a_research.backend.llm.protocol import (
    ChatModelProtocol,
    ChatResponse,
)
from a2a_research.backend.llm.protocol import (
    TestChatModel as ChatModelTestImpl,
)
from a2a_research.backend.llm.providers import OpenRouterChatModel


class TestTestChatModel:
    @pytest.mark.asyncio
    async def test_test_chat_model_returns_configured_response(self) -> None:
        model = ChatModelTestImpl(response_text="custom hello")
        result = await model.ainvoke([{"role": "user", "content": "ping"}])
        assert isinstance(result, ChatResponse)
        assert result.content == "custom hello"


class TestFactory:
    def test_factory_returns_test_model_in_test_mode(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("A2A_TEST_MODE", "1")
        model = create_chat_model()
        assert isinstance(model, ChatModelTestImpl)

    def test_factory_returns_openrouter_in_production(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("A2A_TEST_MODE", raising=False)
        model = create_chat_model()
        assert isinstance(model, OpenRouterChatModel)

    def test_factory_passes_model_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("A2A_TEST_MODE", raising=False)
        model = create_chat_model(model_name="gpt-4")
        assert isinstance(model, OpenRouterChatModel)
        assert model._model == "gpt-4"


class TestProtocolCompliance:
    def test_openrouter_implements_protocol(self) -> None:
        model = OpenRouterChatModel(api_key="test-key")
        assert isinstance(model, ChatModelProtocol)
