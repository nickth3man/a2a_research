"""Tests for the new PocketFlow workflow runtime."""

from __future__ import annotations

from unittest.mock import patch

from a2a_research.agents import _parse_claims_from_analyst, _parse_verified_claims
from a2a_research.models import (
    AgentRole,
    Claim,
    DocumentChunk,
    ResearchSession,
    RetrievedChunk,
    Verdict,
    WorkflowState,
)
from a2a_research.workflow import (
    ActorNode,
    create_actor_node,
    create_pocketflow_workflow,
    get_graph,
    get_workflow,
    run_research_sync,
    run_workflow,
)


def _fake_chunks() -> list[RetrievedChunk]:
    return [
        RetrievedChunk(
            chunk=DocumentChunk(
                id="chunk_1",
                content="RAG combines retrieval with generation to ground answers.",
                source="rag_accuracy",
                chunk_index=0,
            ),
            score=0.91,
        )
    ]


def _responses():
    return [
        '{"research_summary": "RAG uses retrieval."}',
        '{"atomic_claims": [{"id": "c1", "text": "RAG uses retrieval."}]}',
        '{"verified_claims": [{"id": "c1", "text": "RAG uses retrieval.", "verdict": "SUPPORTED", "confidence": 0.85, "sources": ["rag_accuracy"], "evidence_snippets": ["Evidence."]}]}',
        '{"report": "# Report\\n\\nRAG uses retrieval.", "formatted_output": "RAG uses retrieval."}',
    ]


class TestWorkflowBuilder:
    def test_create_pocketflow_workflow_returns_adapter_and_shared(self):
        adapter, shared = create_pocketflow_workflow()
        assert hasattr(adapter, "invoke")
        assert hasattr(adapter, "ainvoke")
        assert hasattr(adapter, "run_async")
        assert "session" in shared
        assert "messages" in shared

    def test_get_workflow_returns_flow_and_shared(self):
        flow, shared = get_workflow()
        assert flow is not None
        assert shared is not None
        assert "session" in shared

    def test_create_actor_node_for_each_role(self):
        for role in [
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.VERIFIER,
            AgentRole.PRESENTER,
        ]:
            node = create_actor_node(role)
            assert isinstance(node, ActorNode)
            assert node.role == role


class TestWorkflowRun:
    async def _run_via_workflow(self, query: str):
        return await run_workflow(query)

    def test_run_workflow_via_run_research_sync(self):
        with (
            patch("a2a_research.agents._call_llm", side_effect=_responses()),
            patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
        ):
            session = run_research_sync("What is RAG?")

        assert session.final_report.startswith("# Report")
        assert set(session.agent_results) == {
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.VERIFIER,
            AgentRole.PRESENTER,
        }
        verified = session.get_agent(AgentRole.VERIFIER)
        assert verified.claims[0].verdict.value == "SUPPORTED"
        assert verified.claims[0].sources == ["rag_accuracy"]

    async def test_run_workflow_async(self):
        with (
            patch("a2a_research.agents._call_llm", side_effect=_responses()),
            patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
        ):
            session = await run_workflow("What is RAG?")
        assert session.final_report.startswith("# Report")
        assert set(session.agent_results) == {
            AgentRole.RESEARCHER,
            AgentRole.ANALYST,
            AgentRole.VERIFIER,
            AgentRole.PRESENTER,
        }


class TestWorkflowAdapter:
    def test_get_graph_returns_invokeable_adapter(self):
        adapter = get_graph()
        assert hasattr(adapter, "invoke")
        assert hasattr(adapter, "ainvoke")

    def test_get_graph_invoke_returns_correct_state_keys(self):
        adapter = get_graph()

        with (
            patch("a2a_research.agents._call_llm", side_effect=_responses()),
            patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
        ):
            state = adapter.invoke(WorkflowState(session=ResearchSession(query="Test?")))

        assert "session" in state
        assert "messages" in state
        assert "current_agent" in state
        assert state["session"].final_report.startswith("# Report")

    async def test_get_graph_ainvoke_returns_correct_state_keys(self):
        adapter = get_graph()
        state = WorkflowState(session=ResearchSession(query="Test?"))

        with (
            patch("a2a_research.agents._call_llm", side_effect=_responses()),
            patch("a2a_research.agents.retrieve", return_value=_fake_chunks()),
        ):
            result = await adapter.ainvoke(state)

        assert "session" in result
        assert "messages" in result
        assert result["session"].final_report.startswith("# Report")


class TestActorNode:
    async def test_actor_node_prep_extracts_session(self):
        from a2a_research.workflow.nodes import ActorNode

        node = ActorNode(AgentRole.RESEARCHER)
        shared = {"session": ResearchSession(query="Test query")}
        prep = await node.prep_async(shared)
        assert prep["session"].query == "Test query"

    async def test_actor_node_prep_raises_on_missing_session(self):
        from a2a_research.workflow.nodes import ActorNode

        node = ActorNode(AgentRole.RESEARCHER)
        shared = {}
        try:
            await node.prep_async(shared)
            raise AssertionError("Expected ValueError")
        except ValueError as e:
            assert "session" in str(e)


class TestClaimParsing:
    def test_parse_claims_from_analyst_normalizes_numeric_ids(self) -> None:
        claims = _parse_claims_from_analyst(
            '{"atomic_claims": [{"id": 1, "text": "RAG uses retrieval."}]}'
        )
        assert [claim.id for claim in claims] == ["1"]

    def test_parse_verified_claims_normalizes_numeric_ids(self) -> None:
        fallback_claims = [Claim(id="c1", text="RAG uses retrieval.", verdict=Verdict.SUPPORTED)]
        claims = _parse_verified_claims(
            (
                '{"verified_claims": [{"id": 1, "text": "RAG uses retrieval.", '
                '"verdict": "SUPPORTED", "confidence": 0.85, '
                '"sources": ["rag_accuracy"], "evidence_snippets": ["Evidence."]}]}'
            ),
            fallback_claims,
        )
        assert [claim.id for claim in claims] == ["1"]
