"""Tests for a2a_research.a2a.cards (build_cards, get_card, AGENT_CARDS)."""

from __future__ import annotations

import pytest
from a2a.types import AgentCard

from a2a_research.backend.core.a2a.card_specs import CARD_SPECS
from a2a_research.backend.core.a2a.cards import (
    AGENT_CARDS,
    build_cards,
    get_card,
)
from a2a_research.backend.core.models import AgentRole


class TestBuildCards:
    def test_returns_dict(self) -> None:
        cards = build_cards()
        assert isinstance(cards, dict)

    def test_all_card_spec_roles_in_result(self) -> None:
        cards = build_cards()
        for role in CARD_SPECS:
            assert role in cards, f"Role {role} missing from build_cards()"

    def test_each_card_is_agent_card(self) -> None:
        cards = build_cards()
        for role, card in cards.items():
            assert isinstance(card, AgentCard), (
                f"Role {role}: expected AgentCard, got {type(card)}"
            )

    def test_card_name_matches_spec(self) -> None:
        cards = build_cards()
        for role, spec in CARD_SPECS.items():
            assert cards[role].name == spec["name"], (
                f"Role {role}: card name mismatch"
            )

    def test_card_description_matches_spec(self) -> None:
        cards = build_cards()
        for role, spec in CARD_SPECS.items():
            assert cards[role].description == spec["description"], (
                f"Role {role}: card description mismatch"
            )

    def test_card_has_skills(self) -> None:
        cards = build_cards()
        for role in CARD_SPECS:
            assert len(cards[role].skills) >= 1, (
                f"Role {role}: card has no skills"
            )

    def test_card_skill_id_matches_spec(self) -> None:
        cards = build_cards()
        for role, spec in CARD_SPECS.items():
            skill_ids = [s.id for s in cards[role].skills]
            assert spec["skill_id"] in skill_ids, (
                f"Role {role}: skill_id {spec['skill_id']!r} not found"
            )

    def test_card_streaming_enabled(self) -> None:
        cards = build_cards()
        for role in CARD_SPECS:
            assert cards[role].capabilities.streaming is True, (
                f"Role {role}: streaming should be True"
            )

    def test_card_has_supported_interfaces(self) -> None:
        cards = build_cards()
        for role in CARD_SPECS:
            assert len(cards[role].supported_interfaces) >= 1, (
                f"Role {role}: no supported interfaces"
            )

    def test_card_url_contains_localhost(self) -> None:
        cards = build_cards()
        for role in CARD_SPECS:
            urls = [iface.url for iface in cards[role].supported_interfaces]
            assert any("localhost" in url for url in urls), (
                f"Role {role}: no localhost URL found in {urls}"
            )


class TestGetCard:
    def test_returns_agent_card(self) -> None:
        card = get_card(AgentRole.PLANNER)
        assert isinstance(card, AgentCard)

    def test_planner_card_name(self) -> None:
        card = get_card(AgentRole.PLANNER)
        assert card.name == "Planner"

    def test_searcher_card_name(self) -> None:
        card = get_card(AgentRole.SEARCHER)
        assert card.name == "Searcher"

    def test_fact_checker_card_name(self) -> None:
        card = get_card(AgentRole.FACT_CHECKER)
        assert card.name == "FactChecker"

    def test_synthesizer_card_name(self) -> None:
        card = get_card(AgentRole.SYNTHESIZER)
        assert card.name == "Synthesizer"

    @pytest.mark.parametrize("role", list(CARD_SPECS.keys()))
    def test_get_card_for_every_role(self, role: AgentRole) -> None:
        card = get_card(role)
        assert isinstance(card, AgentCard)


class TestAgentCardsModule:
    def test_agent_cards_is_dict(self) -> None:
        assert isinstance(AGENT_CARDS, dict)

    def test_agent_cards_contains_planner(self) -> None:
        assert AgentRole.PLANNER in AGENT_CARDS

    def test_agent_cards_contains_fact_checker(self) -> None:
        assert AgentRole.FACT_CHECKER in AGENT_CARDS
