"""Agent activity panel for the loading card."""

import html

import mesop as me

from a2a_research.models import AgentStatus
from a2a_research.ui.tokens import (
    FONT_SIZE_TINY,
)


def _is_verbose_line(line: str) -> bool:
    """Check if an activity line contains verbose prompt details."""
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


def AgentActivityPanel(
    label: str,
    status: AgentStatus,
    lines: list[str],
    retry_count: int = 0,
    error_count: int = 0,
    show_verbose_prompts: bool = True,
) -> None:
    """Render a single agent's activity panel within the loading card."""
    _STATUS_ICON = {
        AgentStatus.PENDING: ("○", "#94a3b8"),
        AgentStatus.RUNNING: ("▸", "#f59e0b"),
        AgentStatus.COMPLETED: ("✓", "#16a34a"),
        AgentStatus.FAILED: ("✗", "#dc2626"),
    }

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
                is_verbose = _is_verbose_line(line)
                if " — " in line and (is_verbose or len(line) > 250):
                    parts = line.split(" — ", 1)
                    summary = parts[0]
                    body = parts[1]
                    is_warn = (
                        "rate limit" in line.lower()
                        or "claim verdict" in line.lower()
                        or "status=error" in line.lower()
                    )
                    line_color = "#d97706" if is_warn else "#1e293b"
                    if not show_verbose_prompts:
                        if is_verbose:
                            me.text(
                                summary + " — hidden",
                                style=me.Style(
                                    margin=me.Margin(bottom=2),
                                    color="#64748b",
                                ),
                            )
                            continue
                        me.text(
                            summary,
                            style=me.Style(
                                margin=me.Margin(bottom=2), color=line_color
                            ),
                        )
                        continue
                    safe_body = html.escape(body[:4096])
                    if len(body) > 4096:
                        safe_body += "\n...[truncated]"
                    html_content = (
                        f'<details><summary style="color:{line_color}">'
                        f"{html.escape(summary)}"
                        f"</summary>"
                        f'<pre style="color:{line_color};'
                        f'white-space:pre-wrap">{safe_body}</pre>'
                        f"</details>"
                    )
                    me.html(html_content)
                else:
                    me.text(
                        line,
                        style=me.Style(margin=me.Margin(bottom=2)),
                    )
