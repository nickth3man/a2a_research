"""Activity line rendering helpers for the agent activity panel."""

from __future__ import annotations

import html

import mesop as me


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


def _render_summary_line(
    summary: str,
    line_color: str,
    show_verbose_prompts: bool,
    is_verbose: bool,
) -> None:
    """Render a non-expandable summary line."""
    if not show_verbose_prompts:
        if is_verbose:
            me.text(
                summary + " — hidden",
                style=me.Style(
                    margin=me.Margin(bottom=2),
                    color="#64748b",
                ),
            )
            return
    me.text(
        summary,
        style=me.Style(
            margin=me.Margin(bottom=2), color=line_color
        ),
    )


def _render_details_block(
    summary: str,
    body: str,
    line_color: str,
) -> None:
    """Render an expandable details/summary HTML block."""
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


def render_activity_line(
    line: str,
    show_verbose_prompts: bool,
) -> None:
    """Render a single activity line with optional details expansion."""
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
        if not show_verbose_prompts and is_verbose:
            _render_summary_line(
                summary, line_color, show_verbose_prompts, is_verbose
            )
            return
        _render_details_block(summary, body, line_color)
    else:
        me.text(
            line,
            style=me.Style(margin=me.Margin(bottom=2)),
        )
