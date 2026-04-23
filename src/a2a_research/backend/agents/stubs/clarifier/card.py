from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill
from a2a_research.backend.core.settings import settings

CLARIFIER_CARD = make_agent_card(
    name="Clarifier",
    description="Disambiguates underspecified queries.",
    url=settings.clarifier_url,
    skills=[
        make_skill(
            skill_id="clarify",
            name="Query Clarification",
            description="Disambiguate and commit to a single interpretation.",
            tags=["clarify", "disambiguate"],
        )
    ],
)
