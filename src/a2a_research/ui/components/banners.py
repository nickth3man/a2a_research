"""Error and loading banners."""

from collections.abc import Callable
from typing import Any

import mesop as me

from a2a_research.models import AgentRole, AgentStatus, ResearchSession
from a2a_research.ui.components.activity import AgentActivityPanel
from a2a_research.ui.style_presets import (
    ERROR_BANNER_STYLE,
    LOADING_CARD_STYLE,
)
from a2a_research.ui.tokens import (
    ERROR_ICON_COLOR,
    ERROR_TEXT,
    LOADING_DOT_SIZE,
)

_ROLE_ORDER = (
    AgentRole.PREPROCESSOR,
    AgentRole.CLARIFIER,
    AgentRole.PLANNER,
    AgentRole.SEARCHER,
    AgentRole.RANKER,
    AgentRole.READER,
    AgentRole.EVIDENCE_DEDUPLICATOR,
    AgentRole.FACT_CHECKER,
    AgentRole.ADVERSARY,
    AgentRole.SYNTHESIZER,
    AgentRole.CRITIC,
    AgentRole.POSTPROCESSOR,
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
    return prefix + error[:max_length] + "…"


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
                    box_shadow=(
                        "0 0 0 4px rgba(245, 158, 11, 0.25),"
                        " 0 0 12px 2px rgba(245, 158, 11, 0.35)"
                    ),
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
                    (
                        "Hide verbose details"
                        if show_verbose_prompts
                        else "Show verbose details"
                    ),
                    on_click=on_toggle_verbose,
                    type="flat",
                )

        for role in _ROLE_ORDER:
            label = _role_label(role)
            agent = session.agent_results.get(role)
            status = agent.status if agent else AgentStatus.PENDING
            lines = activity.get(label, [])
            AgentActivityPanel(
                label=label,
                status=status,
                lines=lines,
                retry_count=(retry_counts or {}).get(label, 0),
                error_count=(error_counts or {}).get(label, 0),
                show_verbose_prompts=bool(show_verbose_prompts),
            )
