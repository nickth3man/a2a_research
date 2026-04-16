"""Agent pipeline timeline card."""

import mesop as me

from a2a_research.models import AgentResult, AgentRole, AgentStatus, ResearchSession
from a2a_research.ui.data_access import get_agent_label, get_all_roles
from a2a_research.ui.primitives import card_box
from a2a_research.ui.tokens import (
    AGENT_ROW_BG_IDLE,
    BORDER_COLOR,
    BORDER_WIDTH,
    FONT_SIZE_BODY,
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    PULSE_BG,
    SECTION_MARGIN_BOTTOM_SM,
    STATUS_LABELS,
    SUBTITLE_MARGIN_BOTTOM,
    TEXT_MUTED,
    status_color,
)


@me.component
def CardTimeline(session: ResearchSession) -> None:  # noqa: N802
    """Display the agent pipeline timeline with status for each agent."""
    with card_box(margin_bottom=SECTION_MARGIN_BOTTOM_SM):
        me.text("Agent Pipeline", type="subtitle-1", style=me.Style(margin=SUBTITLE_MARGIN_BOTTOM))
        for role in get_all_roles(session):
            _render_agent_row(role, session.get_agent(role))


def _render_agent_row(role: AgentRole, result: AgentResult) -> None:
    color = status_color(result.status)
    label = get_agent_label(role)
    icon_map = {
        AgentStatus.COMPLETED: "\u2713",
        AgentStatus.RUNNING: "\u25b8",
        AgentStatus.FAILED: "\u2717",
        AgentStatus.PENDING: "\u25cb",
    }
    status_icon = icon_map.get(result.status, "\u25cb")
    is_running = result.status == AgentStatus.RUNNING
    side = me.BorderSide(width=BORDER_WIDTH, color=BORDER_COLOR)
    left_border = (
        me.BorderSide(width=5, color=color, style="solid")
        if is_running
        else me.BorderSide(width=BORDER_WIDTH, color=BORDER_COLOR)
    )
    pulse_shadow = (
        "0 0 0 1px rgba(59, 130, 246, 0.35), 0 0 12px rgba(59, 130, 246, 0.2)"
        if is_running
        else None
    )

    with me.box(
        style=me.Style(
            display="flex",
            align_items="center",
            gap=12,
            background=PULSE_BG if is_running else AGENT_ROW_BG_IDLE,
            border=me.Border(
                top=me.BorderSide(width=3, color=color),
                right=side,
                bottom=side,
                left=left_border,
            ),
            box_shadow=pulse_shadow,
            padding=me.Padding(top=8, right=10, bottom=8, left=10),
            margin=me.Margin(bottom=6),
        )
    ):
        me.text(status_icon, style=me.Style(color=color, font_size="16px", width=20))
        with me.box(style=me.Style(flex=1)):
            me.text(label, style=me.Style(font_weight="bold", font_size=FONT_SIZE_BODY))
            if result.message:
                me.text(
                    result.message,
                    style=me.Style(
                        color=TEXT_MUTED,
                        font_size=FONT_SIZE_SMALL,
                        font_style="italic" if is_running else "normal",
                    ),
                )
        me.text(
            STATUS_LABELS[result.status],
            style=me.Style(
                color="#fff",
                font_size=FONT_SIZE_TINY,
                background=color,
                padding=me.Padding(top=2, bottom=2, left=8, right=8),
                border_radius=10,
            ),
        )
