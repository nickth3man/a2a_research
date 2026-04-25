from core import make_agent_card, make_skill, settings

ADVERSARY_CARD = make_agent_card(
    name="Adversary",
    description=(
        "Devil's Advocate that seeks counter-evidence for tentatively"
        " supported claims."
    ),
    url=settings.adversary_url,
    skills=[
        make_skill(
            skill_id="adversarial_verify",
            name="Adversarial Verification",
            description="Actively seek counter-evidence for supported claims.",
            tags=["adversary", "counter-evidence", "challenge"],
        )
    ],
)
