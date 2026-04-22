"""Per-agent checklist with secondary sub-step lines for the active step."""

import mesop as me

from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    ResearchSession,
)
from a2a_research.ui.data_access import get_agent_label, get_all_roles
from a2a_research.ui.tokens import (
    FONT_SIZE_SMALL,
    FONT_SIZE_TINY,
    STATUS_LABELS,
    SUBSTEP_COLOR,
    status_color,
)


@me.component
def StepChecklist(  # noqa: N802
    session: ResearchSession,
    granularity: int,
    running_substeps: list[str],
) -> None:
    """Icons and status for each agent; indented sub-steps when
    granularity \u2265 2."""
    for role in get_all_roles(session):
        result = session.get_agent(role)
        _render_checklist_row(role, result, granularity, running_substeps)


def _render_checklist_row(
    role: AgentRole,
    result: AgentResult,
    granularity: int,
    running_substeps: list[str],
) -> None:
    icon_map = {
        AgentStatus.COMPLETED: "\u2713",
        AgentStatus.RUNNING: "\u25b8",
        AgentStatus.FAILED: "\u2717",
        AgentStatus.PENDING: "\u25cb",
    }
    icon = icon_map.get(result.status, "\u25cb")
    label = get_agent_label(role)
    color = status_color(result.status)

    with me.box(
        style=me.Style(
            display="flex",
            flex_direction="column",
            gap=4,
            margin=me.Margin(bottom=10),
            padding=me.Padding(left=4),
        )
    ):
        with me.box(
            style=me.Style(display="flex", align_items="baseline", gap=8)
        ):
            me.text(
                icon, style=me.Style(color=color, font_size="14px", width=18)
            )
            me.text(
                label,
                style=me.Style(
                    font_weight="bold", font_size=FONT_SIZE_SMALL, flex=1
                ),
            )
            me.text(
                STATUS_LABELS[result.status],
                style=me.Style(
                    color="#fff",
                    font_size=FONT_SIZE_TINY,
                    background=color,
                    padding=me.Padding(top=2, bottom=2, left=10, right=10),
                    border_radius=10,
                ),
            )
        if (
            granularity >= 2
            and result.status == AgentStatus.RUNNING
            and running_substeps
        ):
            for line in running_substeps:
                me.text(
                    f"  \u2022 {line}",
                    style=me.Style(
                        font_size=FONT_SIZE_TINY,
                        color=SUBSTEP_COLOR,
                        line_height=1.4,
                        margin=me.Margin(left=26),
                    ),
                )
