"""Miscellaneous event handlers."""

from collections.abc import AsyncGenerator

import mesop as me

from a2a_research.ui.app_state import AppState

from .submit_handler import on_submit


def on_toggle_verbose(_e: me.ClickEvent) -> None:
    """Toggle verbose prompt display in the loading card."""
    state: AppState = me.state(AppState)
    state.show_verbose_prompts = not state.show_verbose_prompts


async def on_retry(e: me.ClickEvent) -> AsyncGenerator[None, None]:
    """Retry the last query by delegating to on_submit."""
    async for _ in on_submit(e):
        yield
