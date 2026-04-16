"""Verified claims panel."""

import mesop as me

from a2a_research.helpers import format_claim_verdict, format_confidence
from a2a_research.models import Claim, ResearchSession
from a2a_research.ui.data_access import get_verified_claims
from a2a_research.ui.primitives import card_box, verdict_badge_text
from a2a_research.ui.tokens import (
    BORDER_WIDTH,
    CLAIM_INNER_RADIUS,
    CLAIM_PADDING,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    SECTION_MARGIN_BOTTOM_MD,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
    build_default_border,
    verdict_bg,
    verdict_color,
)


@me.component
def PanelClaims(session: ResearchSession) -> None:  # noqa: N802
    """Display verified claims with verdict badges and evidence."""
    claims = get_verified_claims(session)
    with card_box(margin_bottom=SECTION_MARGIN_BOTTOM_MD):
        me.text("Verified Claims", type="subtitle-1", style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM))
        if not claims:
            me.text("No verified claims yet — run a query first.", style=me.Style(color=TEXT_MUTED))
            return
        for claim in claims:
            _render_claim(claim)


def _render_claim(claim: Claim) -> None:
    v_color = verdict_color(claim.verdict.value)
    v_bg = verdict_bg(claim.verdict.value)
    badge = format_claim_verdict(claim.verdict)
    conf = format_confidence(claim.confidence)

    with me.box(
        style=me.Style(
            background=v_bg,
            border=build_default_border(),
            border_radius=CLAIM_INNER_RADIUS,
            padding=CLAIM_PADDING,
            margin=me.Margin(bottom=8),
        )
    ):
        with me.box(style=me.Style(display="flex", align_items="flex-start", gap=10)):
            me.text(
                claim.text,
                style=me.Style(flex=1, font_size=FONT_SIZE_BODY, line_height=1.5),
            )
            verdict_badge_text(badge, v_color)

        with me.box(style=me.Style(display="flex", gap=16, margin=me.Margin(top=6))):
            me.text(f"Confidence: {conf}", style=me.Style(font_size=FONT_SIZE_SMALL, color=TEXT_MUTED))
            if claim.sources:
                me.text(
                    f"Sources: {', '.join(claim.sources)}",
                    style=me.Style(font_size=FONT_SIZE_SMALL, color=TEXT_MUTED),
                )

        for snippet in claim.evidence_snippets:
            with me.box(
                style=me.Style(
                    border=me.Border(
                        top=me.BorderSide(width=3, color=f"{v_color}55"),
                        right=me.BorderSide(width=BORDER_WIDTH, color=f"{v_color}55"),
                        bottom=me.BorderSide(width=BORDER_WIDTH, color=f"{v_color}55"),
                        left=me.BorderSide(width=BORDER_WIDTH, color=f"{v_color}55"),
                    ),
                    padding=me.Padding(top=0, right=0, bottom=0, left=10),
                    margin=me.Margin(top=4),
                )
            ):
                me.text(
                    snippet,
                    style=me.Style(font_size=FONT_SIZE_SMALL, color="#374151"),
                )
