"""AgentCard definitions for the research agents."""

from __future__ import annotations

from a2a.types import AgentCard

from a2a_research.a2a.card_specs import CARD_SPECS
from a2a_research.a2a.compat import make_agent_card, make_skill
from a2a_research.models import AgentRole
from a2a_research.settings import settings

__all__ = ["AGENT_CARDS", "build_cards", "get_card"]


def _url_for(role: AgentRole) -> str:
    mapping = {
        AgentRole.PLANNER: settings.planner_url,
        AgentRole.SEARCHER: settings.searcher_url,
        AgentRole.READER: settings.reader_url,
        AgentRole.FACT_CHECKER: settings.fact_checker_url,
        AgentRole.SYNTHESIZER: settings.synthesizer_url,
        AgentRole.CLARIFIER: settings.clarifier_url,
        AgentRole.PREPROCESSOR: settings.preprocessor_url,
        AgentRole.RANKER: settings.ranker_url,
        AgentRole.EVIDENCE_DEDUPLICATOR: settings.evidence_deduplicator_url,
        AgentRole.ADVERSARY: settings.adversary_url,
        AgentRole.CRITIC: settings.critic_url,
        AgentRole.POSTPROCESSOR: settings.postprocessor_url,
    }
    return mapping[role]


def _card(
    role: AgentRole,
    *,
    name: str,
    description: str,
    skill_id: str,
    skill_description: str,
    tags: list[str],
) -> AgentCard:
    skill = make_skill(
        skill_id=skill_id,
        name=name,
        description=skill_description,
        tags=tags,
        input_modes=["text/plain", "application/json"],
        output_modes=["application/json"],
    )
    return make_agent_card(
        name=name,
        description=description,
        url=_url_for(role),
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["application/json"],
        streaming=True,
        skills=[skill],
    )


def build_cards() -> dict[AgentRole, AgentCard]:
    return {
        role: _card(role, **specs)  # type: ignore[arg-type]
        for role, specs in CARD_SPECS.items()
    }


AGENT_CARDS = build_cards()


def get_card(role: AgentRole) -> AgentCard:
    return build_cards()[role]
