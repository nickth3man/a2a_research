from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill

PREPROCESSOR_CARD = make_agent_card(
    name="Preprocessor",
    description="Classifies, sanitizes, and scans queries for PII.",
    url="http://localhost:10006",
    skills=[
        make_skill(
            skill_id="preprocess",
            name="Query Preprocessing",
            description="Classify query type, sanitize, and detect PII.",
            tags=["preprocess", "classify", "sanitize"],
        )
    ],
)
