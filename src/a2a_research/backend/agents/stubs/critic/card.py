from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill
from a2a_research.backend.core.settings import settings

CRITIC_CARD = make_agent_card(
    name="Critic",
    description="Evaluates report quality and suggests improvements.",
    url=settings.critic_url,
    skills=[
        make_skill(
            skill_id="critique",
            name="Report Critique",
            description="Evaluate report quality and suggest improvements.",
            tags=["critique", "quality", "evaluation"],
        )
    ],
)
