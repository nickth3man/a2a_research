"""Tests for a2a_research.a2a.card_specs (CARD_SPECS)."""

from __future__ import annotations

import pytest

from a2a_research.a2a.card_specs import CARD_SPECS
from a2a_research.models import AgentRole

ALL_ROLES = list(AgentRole)
REQUIRED_FIELDS = {
    "name",
    "description",
    "skill_id",
    "skill_description",
    "tags",
}


class TestCardSpecsCompleteness:
    def test_all_agent_roles_covered(self) -> None:
        """Every AgentRole must have an entry in CARD_SPECS."""
        missing = [r for r in ALL_ROLES if r not in CARD_SPECS]
        assert missing == [], f"Roles missing from CARD_SPECS: {missing}"

    def test_no_unknown_roles(self) -> None:
        """CARD_SPECS must not contain roles that are not in AgentRole."""
        valid_roles = set(AgentRole)
        unknown = [r for r in CARD_SPECS if r not in valid_roles]
        assert unknown == [], f"Unknown roles in CARD_SPECS: {unknown}"


class TestCardSpecsStructure:
    @pytest.mark.parametrize("role", list(CARD_SPECS.keys()))
    def test_required_fields_present(self, role: AgentRole) -> None:
        spec = CARD_SPECS[role]
        missing = REQUIRED_FIELDS - spec.keys()
        assert missing == set(), (
            f"Role {role} missing fields: {missing}"
        )

    @pytest.mark.parametrize("role", list(CARD_SPECS.keys()))
    def test_string_fields_non_empty(self, role: AgentRole) -> None:
        spec = CARD_SPECS[role]
        for field in ("name", "description", "skill_id", "skill_description"):
            val = spec[field]
            assert isinstance(val, str), (
                f"Role {role}: field '{field}' is not a str"
            )
            assert val.strip(), (
                f"Role {role}: field '{field}' is empty"
            )

    @pytest.mark.parametrize("role", list(CARD_SPECS.keys()))
    def test_tags_is_non_empty_list_of_strings(
        self, role: AgentRole
    ) -> None:
        spec = CARD_SPECS[role]
        tags = spec["tags"]
        assert isinstance(tags, list), (
            f"Role {role}: 'tags' is not a list"
        )
        assert len(tags) > 0, f"Role {role}: 'tags' is empty"
        for t in tags:
            assert isinstance(t, str), (
                f"Role {role}: tag {t!r} is not a str"
            )


class TestCardSpecsValues:
    def test_planner_skill_id(self) -> None:
        assert CARD_SPECS[AgentRole.PLANNER]["skill_id"] == "query-decomposition"

    def test_searcher_skill_id(self) -> None:
        assert CARD_SPECS[AgentRole.SEARCHER]["skill_id"] == "web-search"

    def test_reader_skill_id(self) -> None:
        assert CARD_SPECS[AgentRole.READER]["skill_id"] == "page-extraction"

    def test_fact_checker_skill_id(self) -> None:
        assert (
            CARD_SPECS[AgentRole.FACT_CHECKER]["skill_id"]
            == "claim-verification"
        )

    def test_synthesizer_skill_id(self) -> None:
        assert (
            CARD_SPECS[AgentRole.SYNTHESIZER]["skill_id"] == "report-synthesis"
        )

    def test_adversary_skill_id(self) -> None:
        assert (
            CARD_SPECS[AgentRole.ADVERSARY]["skill_id"]
            == "adversarial_verify"
        )

    def test_planner_name(self) -> None:
        assert CARD_SPECS[AgentRole.PLANNER]["name"] == "Planner"

    def test_fact_checker_tags_include_verification(self) -> None:
        assert "verification" in CARD_SPECS[AgentRole.FACT_CHECKER]["tags"]

    def test_adversary_tags_include_adversary(self) -> None:
        assert "adversary" in CARD_SPECS[AgentRole.ADVERSARY]["tags"]

    def test_postprocessor_name(self) -> None:
        assert CARD_SPECS[AgentRole.POSTPROCESSOR]["name"] == "Postprocessor"

    def test_evidence_deduplicator_skill_id(self) -> None:
        assert (
            CARD_SPECS[AgentRole.EVIDENCE_DEDUPLICATOR]["skill_id"]
            == "normalize"
        )