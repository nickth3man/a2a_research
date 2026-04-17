"""AgentCard definitions for the five research agents.

Each card declares the agent's identity, skills, and I/O contract. Cards are
used both for A2A discovery and for the UI timeline labels.
"""

from __future__ import annotations

from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from a2a_research.models import AgentRole

__all__ = ["AGENT_CARDS", "get_card"]


def _card(
    role: AgentRole,
    *,
    name: str,
    description: str,
    skill_id: str,
    skill_description: str,
    tags: list[str],
) -> AgentCard:
    skill = AgentSkill(
        id=skill_id,
        name=name,
        description=skill_description,
        tags=tags,
        input_modes=["text/plain", "application/json"],
        output_modes=["application/json"],
    )
    return AgentCard(
        name=name,
        description=description,
        version="1.0.0",
        protocol_version="0.3.0",
        url=f"local://{role.value}",
        preferred_transport="JSONRPC",
        default_input_modes=["text/plain", "application/json"],
        default_output_modes=["application/json"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[skill],
    )


AGENT_CARDS: dict[AgentRole, AgentCard] = {
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
        description="Runs parallel Tavily + DuckDuckGo searches and returns ranked URLs.",
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


def get_card(role: AgentRole) -> AgentCard:
    return AGENT_CARDS[role]
