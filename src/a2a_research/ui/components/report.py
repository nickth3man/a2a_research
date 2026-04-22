"""Final report panel."""

import mesop as me

from a2a_research.backend.core.models import ResearchSession
from a2a_research.ui.primitives import card_box
from a2a_research.ui.tokens import (
    CARD_PADDING,
    CARD_PADDING_LARGE,
    FONT_SIZE_SMALL,
    MARKDOWN_INNER_RADIUS,
    REPORT_MARKDOWN_BG,
    SECTION_MARGIN_BOTTOM_MD,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
    build_default_border,
)


@me.component
def PanelReport(session: ResearchSession) -> None:  # noqa: N802
    """Display the final research report in a markdown panel."""
    with card_box(
        margin_bottom=SECTION_MARGIN_BOTTOM_MD, padding=CARD_PADDING_LARGE
    ):
        me.text(
            "Final Report",
            type="subtitle-1",
            style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM),
        )
        if not session.final_report:
            me.text(
                "Report not ready \u2014 complete the pipeline first.",
                style=me.Style(color=TEXT_MUTED),
            )
            return
        me.text(
            "Tip: select the report below and use Ctrl+C / Cmd+C to copy it.",
            style=me.Style(
                color=TEXT_MUTED,
                font_size=FONT_SIZE_SMALL,
                margin=me.Margin(bottom=12),
            ),
        )
        me.markdown(
            session.final_report,
            style=me.Style(
                background=REPORT_MARKDOWN_BG,
                border=build_default_border(),
                border_radius=MARKDOWN_INNER_RADIUS,
                padding=CARD_PADDING,
            ),
        )
