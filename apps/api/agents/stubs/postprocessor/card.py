from core import make_agent_card, make_skill, settings

POSTPROCESSOR_CARD = make_agent_card(
    name="Postprocessor",
    description="Renders citations, redacts PII, and formats outputs.",
    url=settings.postprocessor_url,
    skills=[
        make_skill(
            skill_id="postprocess",
            name="Output Postprocessing",
            description=(
                "Render citations, redact PII, format markdown/json outputs."
            ),
            tags=["postprocess", "citations", "format"],
        )
    ],
)
