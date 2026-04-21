from a2a_research.a2a.compat import make_agent_card, make_skill

CLARIFIER_CARD = make_agent_card(
    name="Clarifier",
    description="Disambiguates underspecified queries.",
    url="http://localhost:10007",
    skills=[
        make_skill(
            skill_id="clarify",
            name="Query Clarification",
            description="Disambiguate and commit to a single interpretation.",
            tags=["clarify", "disambiguate"],
        )
    ],
)
