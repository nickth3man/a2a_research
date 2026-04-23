from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill
from a2a_research.backend.core.settings import settings

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
