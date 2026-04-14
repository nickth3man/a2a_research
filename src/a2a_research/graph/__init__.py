"""LangGraph workflow — the single orchestrator for the 4-agent pipeline."""

from __future__ import annotations

from typing import Any

from a2a_research.a2a import A2AClient
from a2a_research.models import (
    A2AMessage,
    AgentRole,
    ResearchSession,
    WorkflowState,
)


def _dispatch(
    session: ResearchSession,
    sender: AgentRole,
    recipient: AgentRole,
    payload: dict[str, Any],
) -> A2AMessage:
    client = A2AClient(sender)
    message = A2AMessage(sender=sender, recipient=recipient, payload=payload)
    result = client.send(message, session)
    session.agent_results[recipient] = result
    return message


def researcher_node(state: WorkflowState) -> dict[str, Any]:
    session = state.session
    message = _dispatch(
        session=session,
        sender=AgentRole.RESEARCHER,
        recipient=AgentRole.RESEARCHER,
        payload={"query": session.query},
    )
    state.messages.append(message)
    state.current_agent = AgentRole.RESEARCHER
    return {
        "session": session,
        "messages": list(state.messages),
        "current_agent": state.current_agent,
    }


def analyst_node(state: WorkflowState) -> dict[str, Any]:
    session = state.session
    message = _dispatch(
        session=session,
        sender=AgentRole.RESEARCHER,
        recipient=AgentRole.ANALYST,
        payload={
            "research_summary": session.get_agent(AgentRole.RESEARCHER).raw_content,
            "citations": session.get_agent(AgentRole.RESEARCHER).citations,
        },
    )
    state.messages.append(message)
    state.current_agent = AgentRole.ANALYST
    return {
        "session": session,
        "messages": list(state.messages),
        "current_agent": state.current_agent,
    }


def verifier_node(state: WorkflowState) -> dict[str, Any]:
    session = state.session
    message = _dispatch(
        session=session,
        sender=AgentRole.ANALYST,
        recipient=AgentRole.VERIFIER,
        payload={
            "claims": [
                claim.model_dump() for claim in session.get_agent(AgentRole.ANALYST).claims
            ],
            "query": session.query,
        },
    )
    state.messages.append(message)
    state.current_agent = AgentRole.VERIFIER
    return {
        "session": session,
        "messages": list(state.messages),
        "current_agent": state.current_agent,
    }


def presenter_node(state: WorkflowState) -> dict[str, Any]:
    session = state.session
    message = _dispatch(
        session=session,
        sender=AgentRole.VERIFIER,
        recipient=AgentRole.PRESENTER,
        payload={
            "verified_claims": [
                claim.model_dump() for claim in session.get_agent(AgentRole.VERIFIER).claims
            ],
        },
    )
    state.messages.append(message)
    state.current_agent = AgentRole.PRESENTER
    session.final_report = session.get_agent(AgentRole.PRESENTER).raw_content
    return {
        "session": session,
        "messages": list(state.messages),
        "current_agent": state.current_agent,
    }


def _build_graph_lazy() -> Any:
    from langgraph.graph import END, StateGraph

    workflow = StateGraph(WorkflowState)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("presenter", presenter_node)
    workflow.set_entry_point("researcher")
    workflow.add_edge("researcher", "analyst")
    workflow.add_edge("analyst", "verifier")
    workflow.add_edge("verifier", "presenter")
    workflow.add_edge("presenter", END)
    return workflow


_graph_instance: Any = None


def get_graph() -> Any:
    global _graph_instance
    if _graph_instance is None:
        _graph_instance = _build_graph_lazy().compile()
    return _graph_instance


def run_research_sync(query: str) -> ResearchSession:
    session = ResearchSession(query=query)
    state = WorkflowState(session=session)
    compiled = get_graph()
    final_state = compiled.invoke(state)
    if isinstance(final_state, dict) and "session" in final_state:
        return final_state["session"]
    return session


async def run_research(query: str) -> ResearchSession:
    session = ResearchSession(query=query)
    state = WorkflowState(session=session)
    compiled = get_graph()
    final_state = await compiled.ainvoke(state)
    if isinstance(final_state, dict) and "session" in final_state:
        return final_state["session"]
    return session
