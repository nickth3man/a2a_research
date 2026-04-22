from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill

ADVERSARY_CARD = make_agent_card(
    name="Adversary",
    description=(
        "Devil's Advocate that seeks counter-evidence for tentatively"
        " supported claims."
    ),
    url="http://localhost:10010",
    skills=[
        make_skill(
            skill_id="adversarial_verify",
            name="Adversarial Verification",
            description="Actively seek counter-evidence for supported claims.",
            tags=["adversary", "counter-evidence", "challenge"],
        )
    ],
)
