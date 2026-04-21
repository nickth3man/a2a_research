"""Query input and example handlers."""

import logging

import mesop as me

from a2a_research.app_logging import get_logger, log_event
from a2a_research.models import ResearchSession
from a2a_research.ui.tokens import EXAMPLE_QUERIES

from .app_state import AppState, state_snapshot

logger = get_logger("a2a_research.ui.handlers")


def on_query_input(e: me.InputEvent) -> None:
    """Handle query text input changes."""
    state: AppState = me.state(AppState)
    log_event(
        logger,
        logging.INFO,
        "ui.query.changed",
        length=len(e.value),
        value=e.value,
        previous_value=state.query_text,
    )
    state.query_text = e.value


def _set_example_query(query: str) -> None:
    """Set the query text to an example query."""
    state: AppState = me.state(AppState)
    log_event(
        logger,
        logging.INFO,
        "ui.query.example_selected",
        query=query,
        previous_query=state.query_text,
    )
    state.query_text = query
    state.session = ResearchSession(query=query)


def on_example_a(_e: me.ClickEvent) -> None:
    """Set query to first example."""
    _set_example_query(EXAMPLE_QUERIES[0])


def on_example_b(_e: me.ClickEvent) -> None:
    """Set query to second example."""
    _set_example_query(EXAMPLE_QUERIES[1])


def on_example_c(_e: me.ClickEvent) -> None:
    """Set query to third example."""
    _set_example_query(EXAMPLE_QUERIES[2])
