"""AgentCard definitions for the research agents."""

from __future__ import annotations

from a2a.types import AgentCard

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
        AgentRole.PLANNER: _card(
            AgentRole.PLANNER,
            name="Planner",
            description="Decomposes a research query into atomic claims and seed search queries.",
            skill_id="query-decomposition",
            skill_description="Break a user question into 3-6 atomic verifiable claims.",
            tags=["planning", "decomposition"],
        ),
        AgentRole.SEARCHER: _card(
            AgentRole.SEARCHER,
            name="Searcher",
            description="Runs web search refinement loops and returns ranked URLs.",
            skill_id="web-search",
            skill_description="Concurrent web search with merged, deduplicated results.",
            tags=["search", "retrieval"],
        ),
        AgentRole.READER: _card(
            AgentRole.READER,
            name="Reader",
            description="Fetches URLs and extracts the main text as markdown.",
            skill_id="page-extraction",
            skill_description="Main-content extraction via trafilatura for one or many URLs.",
            tags=["extraction", "reading"],
        ),
        AgentRole.FACT_CHECKER: _card(
            AgentRole.FACT_CHECKER,
            name="FactChecker",
            description=(
                "Coordinates Searcher and Reader in a bounded loop to verify atomic "
                "claims against web evidence until they converge."
            ),
            skill_id="claim-verification",
            skill_description="Iterative verification loop over web evidence.",
            tags=["verification", "loop", "coordination"],
        ),
        AgentRole.SYNTHESIZER: _card(
            AgentRole.SYNTHESIZER,
            name="Synthesizer",
            description="Turns verified claims and cited sources into a structured markdown report.",
            skill_id="report-synthesis",
            skill_description="Structured Pydantic output → markdown report with citations.",
            tags=["synthesis", "writing"],
        ),
    }


AGENT_CARDS = build_cards()


def get_card(role: AgentRole) -> AgentCard:
    return build_cards()[role]
