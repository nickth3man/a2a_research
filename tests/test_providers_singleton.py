"""Tests for provider singleton behavior."""

from __future__ import annotations

import pytest

import a2a_research.backend.llm.providers as providers_module
from a2a_research.backend.llm.providers import (
    get_llm,
    reset_provider_singletons,
)


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
