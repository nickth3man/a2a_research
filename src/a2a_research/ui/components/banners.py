"""Error and loading banners."""

import html
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


def CardLoading(  # noqa: N802
    progress_step_label: str,
    session: ResearchSession,
    running_substeps: list[str],
    activity_by_role: dict[str, list[str]] | None = None,
    retry_counts: dict[str, int] | None = None,
    error_counts: dict[str, int] | None = None,
    show_verbose_prompts: bool = True,
    on_toggle_verbose: Callable[[Any], Any] | None = None,
) -> None:
    """Per-agent live activity feed rendered while the pipeline runs."""
    activity = activity_by_role or {}
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
                style=me.Style(
                    font_weight="bold", font_size="13px", color="#92400e"
                ),
            )
            if on_toggle_verbose is not None:
                me.button(
                    "Hide verbose details"
                    if show_verbose_prompts
                    else "Show verbose details",
                    on_click=on_toggle_verbose,
                    type="flat",
                )

        for role in _ROLE_ORDER:
            label = _role_label(role)
            agent = session.agent_results.get(role)
            status = agent.status if agent else AgentStatus.PENDING
            lines = activity.get(label, [])
            _AgentActivityPanel(
                label=label,
                status=status,
                lines=lines,
                retry_count=(retry_counts or {}).get(label, 0),
                error_count=(error_counts or {}).get(label, 0),
                show_verbose_prompts=bool(show_verbose_prompts),
            )


def _AgentActivityPanel(  # noqa: N802
    label: str,
    status: AgentStatus,
    lines: list[str],
    retry_count: int = 0,
    error_count: int = 0,
    show_verbose_prompts: bool = True,
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
                    font_size="11px", color=color, text_transform="uppercase"
                ),
            )
            if retry_count:
                me.text(
                    f"↻ {retry_count}",
                    style=me.Style(
                        font_size="11px",
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
                        font_size="11px",
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
                    font_size="12px", color="#94a3b8", font_style="italic"
                ),
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
                is_verbose = _is_verbose_line(line)
                if " — " in line and (is_verbose or len(line) > 250):
                    parts = line.split(" — ", 1)
                    summary = parts[0]
                    body = parts[1]
                    is_warning = (
                        "rate limit" in line.lower()
                        or "claim verdict" in line.lower()
                        or "status=error" in line.lower()
                    )
                    color = "#d97706" if is_warning else "#1e293b"
                    if not show_verbose_prompts:
                        if is_verbose:
                            me.text(
                                summary + " — hidden",
                                style=me.Style(
                                    margin=me.Margin(bottom=2), color="#64748b"
                                ),
                            )
                            continue
                        me.text(
                            summary,
                            style=me.Style(
                                margin=me.Margin(bottom=2), color=color
                            ),
                        )
                        continue
                    safe_body = html.escape(body[:4096])
                    if len(body) > 4096:
                        safe_body += "\n...[truncated]"
                    html_content = (
                        f'<details><summary style="color:{color}">{html.escape(summary)}</summary>'
                        f'<pre style="color:{color};white-space:pre-wrap">{safe_body}</pre></details>'
                    )
                    me.html(html_content)
                else:
                    me.text(line, style=me.Style(margin=me.Margin(bottom=2)))


def _is_verbose_line(line: str) -> bool:
    lowered = line.lower()
    return any(
        token in lowered
        for token in (
            "prompt sent",
            "llm response",
            "handoff sent",
            "handoff received",
        )
    )
