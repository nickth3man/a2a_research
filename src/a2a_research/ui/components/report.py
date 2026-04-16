"""Final report panel."""

import mesop as me

from a2a_research.models import ResearchSession
from a2a_research.ui.primitives import card_box
from a2a_research.ui.tokens import (
    CARD_PADDING,
    CARD_PADDING_LARGE,
    MARKDOWN_INNER_RADIUS,
    REPORT_MARKDOWN_BG,
    SECTION_MARGIN_BOTTOM_MD,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
    build_default_border,
)


@me.component
def report_panel(session: ResearchSession) -> None:
    with card_box(margin_bottom=SECTION_MARGIN_BOTTOM_MD, padding=CARD_PADDING_LARGE):
        me.text("Final Report", type="subtitle-1", style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM))
        if not session.final_report:
            me.text(
                "Report not ready — complete the pipeline first.",
                style=me.Style(color=TEXT_MUTED),
            )
            return
        me.markdown(
            session.final_report,
            style=me.Style(
                background=REPORT_MARKDOWN_BG,
                border=build_default_border(),
                border_radius=MARKDOWN_INNER_RADIUS,
                padding=CARD_PADDING,
            ),
        )
