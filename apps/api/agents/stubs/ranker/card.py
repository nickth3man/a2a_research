from core import make_agent_card, make_skill, settings

RANKER_CARD = make_agent_card(
    name="Ranker",
    description="Scores hits by relevance, credibility, and freshness.",
    url=settings.ranker_url,
    skills=[
        make_skill(
            skill_id="rank",
            name="Hit Ranking",
            description=(
                "Rank search hits by claim relevance, credibility, and"
                " freshness."
            ),
            tags=["rank", "score", "credibility"],
        )
    ],
)
