"""Tests for a2a_research.a2a.compat (make_skill, make_agent_card)."""

from __future__ import annotations

import pytest
from a2a.types import AgentCard, AgentSkill

from a2a_research.a2a.compat import make_agent_card, make_skill


class TestMakeSkill:
    def test_returns_agent_skill(self) -> None:
        skill = make_skill(
            skill_id="test-skill",
            name="Test",
            description="A test skill",
        )
        assert isinstance(skill, AgentSkill)

    def test_skill_id_and_name_set(self) -> None:
        skill = make_skill(
            skill_id="my-id",
            name="My Name",
            description="desc",
        )
        assert skill.id == "my-id"
        assert skill.name == "My Name"

    def test_description_set(self) -> None:
        skill = make_skill(
            skill_id="s",
            name="n",
            description="a description",
        )
        assert skill.description == "a description"

    def test_tags_default_to_empty(self) -> None:
        skill = make_skill(
            skill_id="s", name="n", description="d"
        )
        assert skill.tags == []

    def test_tags_provided(self) -> None:
        skill = make_skill(
            skill_id="s",
            name="n",
            description="d",
            tags=["a", "b"],
        )
        assert skill.tags == ["a", "b"]

    def test_examples_default_to_empty(self) -> None:
        skill = make_skill(
            skill_id="s", name="n", description="d"
        )
        assert skill.examples == []

    def test_examples_provided(self) -> None:
        skill = make_skill(
            skill_id="s",
            name="n",
            description="d",
            examples=["ex1", "ex2"],
        )
        assert skill.examples == ["ex1", "ex2"]

    def test_input_modes_provided(self) -> None:
        skill = make_skill(
            skill_id="s",
            name="n",
            description="d",
            input_modes=["text/plain"],
        )
        assert "text/plain" in skill.input_modes

    def test_output_modes_provided(self) -> None:
        skill = make_skill(
            skill_id="s",
            name="n",
            description="d",
            output_modes=["application/json"],
        )
        assert "application/json" in skill.output_modes


class TestMakeAgentCard:
    def test_returns_agent_card(self) -> None:
        card = make_agent_card(
            name="Test Agent",
            description="A test agent",
            url="http://localhost:9999",
        )
        assert isinstance(card, AgentCard)

    def test_name_and_description(self) -> None:
        card = make_agent_card(
            name="MyAgent",
            description="does stuff",
            url="http://localhost:1",
        )
        assert card.name == "MyAgent"
        assert card.description == "does stuff"

    def test_url_in_supported_interfaces(self) -> None:
        url = "http://localhost:12345"
        card = make_agent_card(
            name="A", description="b", url=url
        )
        urls = [iface.url for iface in card.supported_interfaces]
        assert url in urls

    def test_streaming_default_false(self) -> None:
        card = make_agent_card(
            name="A", description="b", url="http://x"
        )
        assert card.capabilities.streaming is False

    def test_streaming_true(self) -> None:
        card = make_agent_card(
            name="A",
            description="b",
            url="http://x",
            streaming=True,
        )
        assert card.capabilities.streaming is True

    def test_version_default(self) -> None:
        card = make_agent_card(
            name="A", description="b", url="http://x"
        )
        assert card.version == "1.0.0"

    def test_version_custom(self) -> None:
        card = make_agent_card(
            name="A",
            description="b",
            url="http://x",
            version="2.3.4",
        )
        assert card.version == "2.3.4"

    def test_default_input_modes(self) -> None:
        card = make_agent_card(
            name="A",
            description="b",
            url="http://x",
            default_input_modes=["text/plain"],
        )
        assert "text/plain" in card.default_input_modes

    def test_default_output_modes(self) -> None:
        card = make_agent_card(
            name="A",
            description="b",
            url="http://x",
            default_output_modes=["application/json"],
        )
        assert "application/json" in card.default_output_modes

    def test_skills_attached(self) -> None:
        skill = make_skill(
            skill_id="sk",
            name="Sk",
            description="sd",
        )
        card = make_agent_card(
            name="A",
            description="b",
            url="http://x",
            skills=[skill],
        )
        assert len(card.skills) == 1
        assert card.skills[0].id == "sk"

    def test_empty_skills_by_default(self) -> None:
        card = make_agent_card(
            name="A", description="b", url="http://x"
        )
        assert card.skills == []

    def test_push_notifications_default_false(self) -> None:
        card = make_agent_card(
            name="A", description="b", url="http://x"
        )
        assert card.capabilities.push_notifications is False