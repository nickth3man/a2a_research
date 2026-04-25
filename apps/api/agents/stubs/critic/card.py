from core import make_agent_card, make_skill, settings

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
