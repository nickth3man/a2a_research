import mesop as me

from a2a_research.helpers import format_claim_verdict, format_confidence
from a2a_research.models import AgentRole, AgentStatus, Claim, ResearchSession

AGENT_LABELS = {
    AgentRole.RESEARCHER: "Researcher",
    AgentRole.ANALYST: "Analyst",
    AgentRole.VERIFIER: "Verifier",
    AgentRole.PRESENTER: "Presenter",
}
ALL_ROLES = [AgentRole.RESEARCHER, AgentRole.ANALYST, AgentRole.VERIFIER, AgentRole.PRESENTER]


def _status_color(status: AgentStatus) -> str:
    if status == AgentStatus.COMPLETED:
        return "#16a34a"
    if status == AgentStatus.RUNNING:
        return "#d97706"
    if status == AgentStatus.FAILED:
        return "#dc2626"
    return "#9ca3af"


def _verdict_color(verdict: str) -> str:
    if verdict == "SUPPORTED":
        return "#16a34a"
    if verdict == "REFUTED":
        return "#dc2626"
    return "#d97706"


def _verdict_bg(verdict: str) -> str:
    if verdict == "SUPPORTED":
        return "#dcfce7"
    if verdict == "REFUTED":
        return "#fee2e2"
    return "#fef3c7"


@me.component
def agent_timeline_card(session: ResearchSession):
    with me.box(style=me.Style(margin=me.Margin(bottom=16))):
        with me.box(
            style=me.Style(
                background="#fff",
                border_radius=10,
                box_shadow="0 1px 3px rgba(0,0,0,0.08)",
                border=me.Border(
                    top=me.BorderSide(width=1, color="#e5e7eb"),
                    right=me.BorderSide(width=1, color="#e5e7eb"),
                    bottom=me.BorderSide(width=1, color="#e5e7eb"),
                    left=me.BorderSide(width=1, color="#e5e7eb"),
                ),
                padding=me.Padding(top=16, right=16, bottom=16, left=16),
            )
        ):
            me.text(
                "Agent Pipeline", type="subtitle-1", style=me.Style(margin=me.Margin(bottom=12))
            )
            for role in ALL_ROLES:
                _render_agent_row(role, session.get_agent(role))


def _render_agent_row(role: AgentRole, result):
    color = _status_color(result.status)
    label = AGENT_LABELS.get(role, role.value)
    icon_map = {
        AgentStatus.COMPLETED: "✓",
        AgentStatus.RUNNING: "▸",
        AgentStatus.FAILED: "✗",
        AgentStatus.PENDING: "○",
    }
    status_icon = icon_map.get(result.status, "○")

    with me.box(
        style=me.Style(
            display="flex",
            align_items="center",
            gap=12,
            background="#f9fafb" if result.status != AgentStatus.RUNNING else "#fffbeb",
            border=me.Border(
                top=me.BorderSide(width=3, color=color),
                right=me.BorderSide(width=1, color="#e5e7eb"),
                bottom=me.BorderSide(width=1, color="#e5e7eb"),
                left=me.BorderSide(width=1, color="#e5e7eb"),
            ),
            padding=me.Padding(top=8, right=10, bottom=8, left=10),
            margin=me.Margin(bottom=6),
        )
    ):
        me.text(status_icon, style=me.Style(color=color, font_size="16px", width=20))
        with me.box(style=me.Style(flex=1)):
            me.text(label, style=me.Style(font_weight="bold", font_size="14px"))
            if result.message:
                me.text(result.message, style=me.Style(color="#6b7280", font_size="12px"))
        me.text(
            result.status.value,
            style=me.Style(
                color="#fff",
                font_size="11px",
                background=color,
                padding=me.Padding(top=2, bottom=2, left=8, right=8),
                border_radius=10,
            ),
        )


@me.component
def claims_panel(session: ResearchSession):
    claims = session.get_agent(AgentRole.VERIFIER).claims
    with me.box(style=me.Style(margin=me.Margin(bottom=20))):
        with me.box(
            style=me.Style(
                background="#fff",
                border_radius=10,
                box_shadow="0 1px 3px rgba(0,0,0,0.08)",
                border=me.Border(
                    top=me.BorderSide(width=1, color="#e5e7eb"),
                    right=me.BorderSide(width=1, color="#e5e7eb"),
                    bottom=me.BorderSide(width=1, color="#e5e7eb"),
                    left=me.BorderSide(width=1, color="#e5e7eb"),
                ),
                padding=me.Padding(top=16, right=16, bottom=16, left=16),
            )
        ):
            me.text(
                "Verified Claims", type="subtitle-1", style=me.Style(margin=me.Margin(bottom=12))
            )
            if not claims:
                me.text(
                    "No verified claims yet — run a query first.", style=me.Style(color="#6b7280")
                )
                return
            for claim in claims:
                _render_claim(claim)


def _render_claim(claim: Claim):
    v_color = _verdict_color(claim.verdict.value)
    v_bg = _verdict_bg(claim.verdict.value)
    badge = format_claim_verdict(claim.verdict)
    conf = format_confidence(claim.confidence)

    with me.box(
        style=me.Style(
            background=v_bg,
            border=me.Border(
                top=me.BorderSide(width=1, color="#e5e7eb"),
                right=me.BorderSide(width=1, color="#e5e7eb"),
                bottom=me.BorderSide(width=1, color="#e5e7eb"),
                left=me.BorderSide(width=1, color="#e5e7eb"),
            ),
            border_radius=8,
            padding=me.Padding(top=14, right=14, bottom=14, left=14),
            margin=me.Margin(bottom=8),
        )
    ):
        with me.box(style=me.Style(display="flex", align_items="flex-start", gap=10)):
            me.text(
                claim.text,
                style=me.Style(flex=1, font_size="14px", line_height=1.5),
            )
            me.text(
                badge,
                style=me.Style(
                    color=v_color,
                    font_size="11px",
                    background="#fff",
                    padding=me.Padding(top=2, bottom=2, left=8, right=8),
                    border_radius=4,
                    border=me.Border(
                        top=me.BorderSide(width=1, color=v_color),
                        right=me.BorderSide(width=1, color=v_color),
                        bottom=me.BorderSide(width=1, color=v_color),
                        left=me.BorderSide(width=1, color=v_color),
                    ),
                ),
            )

        with me.box(style=me.Style(display="flex", gap=16, margin=me.Margin(top=6))):
            me.text(f"Confidence: {conf}", style=me.Style(font_size="12px", color="#6b7280"))
            if claim.sources:
                me.text(
                    f"Sources: {', '.join(claim.sources)}",
                    style=me.Style(font_size="12px", color="#6b7280"),
                )

        for snippet in claim.evidence_snippets:
            with me.box(
                style=me.Style(
                    border=me.Border(
                        top=me.BorderSide(width=3, color=f"{v_color}55"),
                        right=me.BorderSide(width=1, color=f"{v_color}55"),
                        bottom=me.BorderSide(width=1, color=f"{v_color}55"),
                        left=me.BorderSide(width=1, color=f"{v_color}55"),
                    ),
                    padding=me.Padding(top=0, right=0, bottom=0, left=10),
                    margin=me.Margin(top=4),
                )
            ):
                me.text(
                    snippet,
                    style=me.Style(font_size="12px", color="#374151"),
                )


@me.component
def sources_panel(session: ResearchSession):
    researcher = session.get_agent(AgentRole.RESEARCHER)
    verifier = session.get_agent(AgentRole.VERIFIER)
    all_citations = list(dict.fromkeys(researcher.citations + verifier.citations))

    with me.box(style=me.Style(margin=me.Margin(bottom=20))):
        with me.box(
            style=me.Style(
                background="#fff",
                border_radius=10,
                box_shadow="0 1px 3px rgba(0,0,0,0.08)",
                border=me.Border(
                    top=me.BorderSide(width=1, color="#e5e7eb"),
                    right=me.BorderSide(width=1, color="#e5e7eb"),
                    bottom=me.BorderSide(width=1, color="#e5e7eb"),
                    left=me.BorderSide(width=1, color="#e5e7eb"),
                ),
                padding=me.Padding(top=16, right=16, bottom=16, left=16),
            )
        ):
            me.text(
                "Sources & Citations",
                type="subtitle-1",
                style=me.Style(margin=me.Margin(bottom=12)),
            )
            if not all_citations:
                me.text("No sources cited yet.", style=me.Style(color="#6b7280"))
                return

            for i, src in enumerate(all_citations, 1):
                src_display = src.replace("_", " ").replace("-", " ").title()
                with me.box(
                    style=me.Style(
                        display="flex",
                        align_items="center",
                        gap=8,
                        background="#f3f4f6",
                        border_radius=6,
                        padding=me.Padding(top=8, right=8, bottom=8, left=8),
                        margin=me.Margin(bottom=4),
                    )
                ):
                    me.text(
                        str(i),
                        style=me.Style(
                            background="#6b7280",
                            color="#fff",
                            font_size="11px",
                            width=20,
                            height=20,
                            border_radius=10,
                            text_align="center",
                        ),
                    )
                    me.text(src_display, style=me.Style(font_size="13px", flex=1))


@me.component
def report_panel(session: ResearchSession):
    with me.box(style=me.Style(margin=me.Margin(bottom=20))):
        with me.box(
            style=me.Style(
                background="#fff",
                border_radius=10,
                box_shadow="0 1px 3px rgba(0,0,0,0.08)",
                border=me.Border(
                    top=me.BorderSide(width=1, color="#e5e7eb"),
                    right=me.BorderSide(width=1, color="#e5e7eb"),
                    bottom=me.BorderSide(width=1, color="#e5e7eb"),
                    left=me.BorderSide(width=1, color="#e5e7eb"),
                ),
                padding=me.Padding(top=20, right=20, bottom=20, left=20),
            )
        ):
            me.text("Final Report", type="subtitle-1", style=me.Style(margin=me.Margin(bottom=12)))
            if not session.final_report:
                me.text(
                    "Report not ready — complete the pipeline first.",
                    style=me.Style(color="#6b7280"),
                )
                return
            me.markdown(
                session.final_report,
                style=me.Style(
                    background="#fafafa",
                    border=me.Border(
                        top=me.BorderSide(width=1, color="#e5e7eb"),
                        right=me.BorderSide(width=1, color="#e5e7eb"),
                        bottom=me.BorderSide(width=1, color="#e5e7eb"),
                        left=me.BorderSide(width=1, color="#e5e7eb"),
                    ),
                    border_radius=6,
                    padding=me.Padding(top=16, right=16, bottom=16, left=16),
                ),
            )


@me.component
def query_input_card(on_submit, on_query_input, query_text: str):
    with me.box(
        style=me.Style(
            background="#fff",
            border_radius=10,
            box_shadow="0 1px 3px rgba(0,0,0,0.08)",
            border=me.Border(
                top=me.BorderSide(width=1, color="#e5e7eb"),
                right=me.BorderSide(width=1, color="#e5e7eb"),
                bottom=me.BorderSide(width=1, color="#e5e7eb"),
                left=me.BorderSide(width=1, color="#e5e7eb"),
            ),
            padding=me.Padding(top=20, right=20, bottom=20, left=20),
            margin=me.Margin(bottom=16),
        )
    ):
        me.text(
            "Research Query",
            type="subtitle-1",
            style=me.Style(margin=me.Margin(bottom=12)),
        )
        me.textarea(
            label="Enter your research question…",
            key="query",
            value=query_text,
            rows=3,
            on_input=on_query_input,
            style=me.Style(margin=me.Margin(bottom=12)),
        )
        with me.box(style=me.Style(display="flex", justify_content="end")):
            me.button(
                "Run Research",
                on_click=on_submit,
                type="flat",
                color="primary",
            )


@me.component
def error_banner(error: str):
    with me.box(
        style=me.Style(
            background="#fef2f2",
            border=me.Border(
                top=me.BorderSide(width=1, color="#fecaca"),
                right=me.BorderSide(width=1, color="#fecaca"),
                bottom=me.BorderSide(width=1, color="#fecaca"),
                left=me.BorderSide(width=1, color="#fecaca"),
            ),
            border_radius=8,
            padding=me.Padding(top=14, right=14, bottom=14, left=14),
            margin=me.Margin(bottom=16),
            display="flex",
            align_items="center",
            gap=12,
        )
    ):
        me.text(
            f"Pipeline error: {error[:200]}…", style=me.Style(color="#dc2626", font_size="14px")
        )


@me.component
def loading_card(session: ResearchSession):
    with me.box(
        style=me.Style(
            text_align="center",
            background="#fffbeb",
            border=me.Border(
                top=me.BorderSide(width=1, color="#fde68a"),
                right=me.BorderSide(width=1, color="#fde68a"),
                bottom=me.BorderSide(width=1, color="#fde68a"),
                left=me.BorderSide(width=1, color="#fde68a"),
            ),
            border_radius=10,
            padding=me.Padding(top=32, right=32, bottom=32, left=32),
            margin=me.Margin(bottom=20),
        )
    ):
        me.text(
            "Running research pipeline…",
            style=me.Style(font_size="15px", color="#92400e", font_weight="bold"),
        )
        me.text(
            "Researchers retrieving documents · Analysts decomposing · "
            "Verifiers checking evidence · Presenter rendering",
            style=me.Style(font_size="12px", color="#92400e", margin=me.Margin(top=8)),
        )
    agent_timeline_card(session)
