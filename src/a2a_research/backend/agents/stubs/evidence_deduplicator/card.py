from a2a_research.backend.core.a2a.compat import make_agent_card, make_skill
from a2a_research.backend.core.settings import settings

EVIDENCE_DEDUPLICATOR_CARD = make_agent_card(
    name="EvidenceDeduplicator",
    description=(
        "Normalizes and deduplicates evidence with source independence"
        " tracking."
    ),
    url=settings.evidence_deduplicator_url,
    skills=[
        make_skill(
            skill_id="normalize",
            name="Evidence Normalization",
            description=(
                "Deduplicate evidence and compute source independence."
            ),
            tags=["deduplicate", "normalize", "independence"],
        )
    ],
)
