"""Agent activity panel for the loading card."""

import mesop as me

from a2a_research.backend.core.models import AgentStatus
from a2a_research.ui.components.activity_render import render_activity_line
from a2a_research.ui.tokens import (
    FONT_SIZE_TINY,
)


def AgentActivityPanel(  # noqa: N802
    label: str,
    status: AgentStatus,
    lines: list[str],
    retry_count: int = 0,
    error_count: int = 0,
    show_verbose_prompts: bool = True,
) -> None:
    """Render a single agent's activity panel within the loading card."""
    _status_icon = {
        AgentStatus.PENDING: ("○", "#94a3b8"),
        AgentStatus.RUNNING: ("▸", "#f59e0b"),
        AgentStatus.COMPLETED: ("✓", "#16a34a"),
        AgentStatus.FAILED: ("✗", "#dc2626"),
    }

    icon, color = _status_icon[status]
    with me.box(
        style=me.Style(
            margin=me.Margin(bottom=10),
            padding=me.Padding.all(10),
            border_radius=8,
            background="#ffffff",
            border=me.Border.all(me.BorderSide(width=1, color="#e2e8f0")),
        )
    ):
        with me.box(
            style=me.Style(
                display="flex",
                align_items="center",
                gap=8,
                margin=me.Margin(bottom=6),
            )
        ):
            me.text(
                icon,
                style=me.Style(
                    color=color, font_size="16px", font_weight="bold"
                ),
            )
            me.text(
                label,
                style=me.Style(
                    font_weight="bold", font_size="14px", color="#0f172a"
                ),
            )
            me.text(
                status.value,
                style=me.Style(
                    font_size=FONT_SIZE_TINY,
                    color=color,
                    text_transform="uppercase",
                ),
            )
            if retry_count:
                me.text(
                    f"↻ {retry_count}",
                    style=me.Style(
                        font_size=FONT_SIZE_TINY,
                        color="#f59e0b",
                        background="#fffbeb",
                        padding=me.Padding.symmetric(horizontal=4, vertical=2),
                        border_radius=4,
                    ),
                )
            if error_count:
                me.text(
                    f"✗ {error_count}",
                    style=me.Style(
                        font_size=FONT_SIZE_TINY,
                        color="#dc2626",
                        background="#fef2f2",
                        padding=me.Padding.symmetric(horizontal=4, vertical=2),
                        border_radius=4,
                    ),
                )
        if not lines:
            me.text(
                "(no activity yet)",
                style=me.Style(
                    font_size="12px",
                    color="#94a3b8",
                    font_style="italic",
                ),
            )
            return

        with me.box(
            style=me.Style(
                max_height=200,
                overflow_y="auto",
                font_family=("ui-monospace, SFMono-Regular, Menlo, monospace"),
                font_size="12px",
                color="#1e293b",
                background="#f8fafc",
                padding=me.Padding.all(8),
                border_radius=6,
            )
        ):
            for line in reversed(lines):
                render_activity_line(line, show_verbose_prompts)
