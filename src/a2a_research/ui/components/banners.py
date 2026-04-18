"""Error and loading banners."""

from collections.abc import Callable
from typing import Any

import mesop as me

from a2a_research.models import AgentRole, AgentStatus, ResearchSession
from a2a_research.ui.tokens import (
    ERROR_BANNER_STYLE,
    ERROR_ICON_COLOR,
    ERROR_TEXT,
    LOADING_CARD_STYLE,
    LOADING_DOT_SIZE,
)

_ROLE_ORDER = (
    AgentRole.PLANNER,
    AgentRole.SEARCHER,
    AgentRole.READER,
    AgentRole.FACT_CHECKER,
    AgentRole.SYNTHESIZER,
)


def _role_label(role: AgentRole) -> str:
    return role.value.replace("_", " ").title()


_STATUS_ICON = {
    AgentStatus.PENDING: ("○", "#94a3b8"),
    AgentStatus.RUNNING: ("▸", "#f59e0b"),
    AgentStatus.COMPLETED: ("✓", "#16a34a"),
    AgentStatus.FAILED: ("✗", "#dc2626"),
}


@me.component
def BannerError(  # noqa: N802
    error: str, *, on_retry: Callable[[Any], Any] | None = None
) -> None:
    """Display an error banner with left-border accent and retry action."""
    with me.box(style=ERROR_BANNER_STYLE):
        me.icon(
            "error_outline",
            style=me.Style(
                font_size="20px",
                color=ERROR_ICON_COLOR,
                flex_shrink=0,
            ),
        )
        me.text(
            _error_banner_message(error),
            style=me.Style(
                color=ERROR_TEXT,
                font_size="15px",
                font_weight=500,
                flex_grow=1,
            ),
        )
        if on_retry is not None:
            me.button("Retry", on_click=on_retry, type="flat", color="warn")


def _error_banner_message(error: str, *, max_length: int = 200) -> str:
    """Format an error message with prefix and length limit."""
    prefix = "Pipeline error: "
    if len(error) <= max_length:
        return prefix + error
    return prefix + error[:max_length] + "\u2026"


@me.component
def CardLoading(  # noqa: N802
    progress_step_label: str,
    session: ResearchSession,
    running_substeps: list[str],
    activity_by_role: dict[str, list[str]],
) -> None:
    """Per-agent live activity feed rendered while the pipeline runs."""
    with me.box(style=LOADING_CARD_STYLE):
        with me.box(
            style=me.Style(
                width="100%",
                margin=me.Margin(bottom=16),
                display="flex",
                align_items="center",
                justify_content="center",
                gap=8,
            )
        ):
            with me.box(
                style=me.Style(
                    width=LOADING_DOT_SIZE,
                    height=LOADING_DOT_SIZE,
                    border_radius="9999px",
                    background="#f59e0b",
                    box_shadow="0 0 0 4px rgba(245, 158, 11, 0.25), 0 0 12px 2px rgba(245, 158, 11, 0.35)",
                )
            ):
                pass
            me.text(
                progress_step_label or "Pipeline starting",
                style=me.Style(font_weight="bold", font_size="13px", color="#92400e"),
            )

        for role in _ROLE_ORDER:
            label = _role_label(role)
            agent = session.agent_results.get(role)
            status = agent.status if agent else AgentStatus.PENDING
            lines = activity_by_role.get(label, [])
            _AgentActivityPanel(label=label, status=status, lines=lines)


@me.component
def _AgentActivityPanel(  # noqa: N802
    label: str, status: AgentStatus, lines: list[str]
) -> None:
    icon, color = _STATUS_ICON[status]
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
            me.text(icon, style=me.Style(color=color, font_size="16px", font_weight="bold"))
            me.text(
                label,
                style=me.Style(font_weight="bold", font_size="14px", color="#0f172a"),
            )
            me.text(
                status.value,
                style=me.Style(font_size="11px", color=color, text_transform="uppercase"),
            )
        if not lines:
            me.text(
                "(no activity yet)",
                style=me.Style(font_size="12px", color="#94a3b8", font_style="italic"),
            )
            return
        # Render most-recent-first, capped to a scrollable window.
        with me.box(
            style=me.Style(
                max_height=200,
                overflow_y="auto",
                font_family="ui-monospace, SFMono-Regular, Menlo, monospace",
                font_size="12px",
                color="#1e293b",
                background="#f8fafc",
                padding=me.Padding.all(8),
                border_radius=6,
            )
        ):
            for line in reversed(lines):
                me.text(line, style=me.Style(margin=me.Margin(bottom=2)))
