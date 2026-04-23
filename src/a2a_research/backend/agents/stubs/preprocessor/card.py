from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill
from a2a_research.backend.core.settings import settings

PREPROCESSOR_CARD = make_agent_card(
    name="Preprocessor",
    description="Classifies, sanitizes, and scans queries for PII.",
    url=settings.preprocessor_url,
    skills=[
        make_skill(
            skill_id="preprocess",
            name="Query Preprocessing",
            description="Classify query type, sanitize, and detect PII.",
            tags=["preprocess", "classify", "sanitize"],
        )
    ],
)
