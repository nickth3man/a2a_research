"""Focused workflow tests for orchestration and presenter contract handling."""

from __future__ import annotations

from unittest.mock import patch

from a2a_research.models import (
    AgentRole,
    DocumentChunk,
    ResearchSession,
    RetrievedChunk,
    WorkflowState,
)
from a2a_research.workflow import get_graph, run_research_sync


def _fake_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk=DocumentChunk(
                id="chunk_1",
                content="RAG combines retrieval with generation to ground answers in documents.",
                source="rag_accuracy",
                chunk_index=0,
                metadata={"title": "RAG Accuracy"},
            ),
            score=0.91,
        )
    ]


def test_run_research_sync_returns_markdown_report_from_presenter_json() -> None:
    responses = [
        '{"research_summary": "RAG grounds model responses in retrieved documents."}',
        '{"atomic_claims": [{"id": "c1", "text": "RAG grounds responses in retrieved documents."}]}',
        '{"verified_claims": [{"id": "c1", "text": "RAG grounds responses in retrieved documents.", "verdict": "SUPPORTED", "confidence": 0.9, "sources": ["rag_accuracy"], "evidence_snippets": ["Retrieved documents ground the response."]}]}',
        '{"report": "# Final Report\\n\\nRAG uses retrieved evidence.", "formatted_output": "RAG uses retrieved evidence."}',
    ]

    with (
        patch("a2a_research.agents._call_llm", side_effect=responses),
        patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
    ):
        session = run_research_sync("How does RAG work?")

    assert session.final_report.startswith("# Final Report")
    assert set(session.agent_results) == {
        AgentRole.RESEARCHER,
        AgentRole.ANALYST,
        AgentRole.VERIFIER,
        AgentRole.PRESENTER,
    }
    assert session.get_agent(AgentRole.VERIFIER).claims[0].sources == ["rag_accuracy"]


def test_workflow_state_records_a2a_message_handoffs() -> None:
    responses = [
        '{"research_summary": "RAG uses retrieval."}',
        '{"atomic_claims": [{"id": "c1", "text": "RAG uses retrieval."}]}',
        '{"verified_claims": [{"id": "c1", "text": "RAG uses retrieval.", "verdict": "SUPPORTED", "confidence": 0.8, "sources": ["rag_accuracy"], "evidence_snippets": ["The corpus describes retrieval."]}]}',
        '{"report": "# Report\\n\\nRAG uses retrieval.", "formatted_output": "RAG uses retrieval."}',
    ]

    with (
        patch("a2a_research.agents._call_llm", side_effect=responses),
        patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
    ):
        initial_state = WorkflowState(session=ResearchSession(query="What is RAG?"))
        final_state = get_graph().invoke(initial_state)

    assert [message.recipient for message in final_state["messages"]] == [
        AgentRole.RESEARCHER,
        AgentRole.ANALYST,
        AgentRole.VERIFIER,
        AgentRole.PRESENTER,
    ]
    assert final_state["session"].final_report.startswith("# Report")
