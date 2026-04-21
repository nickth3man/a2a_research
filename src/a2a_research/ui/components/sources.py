"""Sources and citations panel."""

import mesop as me

from a2a_research.models import ResearchSession
from a2a_research.ui.data_access import get_all_citations
from a2a_research.ui.formatting import format_source_display
from a2a_research.ui.primitives import card_box
from a2a_research.ui.tokens import (
    FONT_SIZE_TINY,
    SECTION_MARGIN_BOTTOM_MD,
    SOURCE_ROW_BG,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
)


@me.component
def PanelSources(session: ResearchSession) -> None:  # noqa: N802
    """Display aggregated sources and citations from all agents."""
    all_citations = get_all_citations(session)

    with card_box(margin_bottom=SECTION_MARGIN_BOTTOM_MD):
        me.text(
            "Sources & Citations",
            type="subtitle-1",
            style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM),
        )
        if not all_citations:
            me.text("No sources cited yet.", style=me.Style(color=TEXT_MUTED))
            return

        for i, citation in enumerate(all_citations, 1):
            formatted_citation = format_source_display(citation)
            with me.box(
                style=me.Style(
                    display="flex",
                    align_items="center",
                    gap=8,
                    background=SOURCE_ROW_BG,
                    border_radius=6,
                    padding=me.Padding(top=8, right=8, bottom=8, left=8),
                    margin=me.Margin(bottom=4),
                )
            ):
                me.text(
                    str(i),
                    style=me.Style(
                        background=TEXT_MUTED,
                        color="#fff",
                        font_size=FONT_SIZE_TINY,
                        width=20,
                        height=20,
                        border_radius=10,
                        text_align="center",
                    ),
                )
                me.text(
                    formatted_citation,
                    style=me.Style(font_size="13px", flex=1),
                )
