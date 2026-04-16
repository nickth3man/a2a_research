"""Focused tests for pure logic and state contracts."""

from __future__ import annotations

import pytest

from a2a_research.helpers import (
    aggregate_citations,
    build_markdown_report,
    create_result,
    extract_claims_from_llm_output,
    format_claim_verdict,
    format_claims_section,
    format_confidence,
    parse_json_safely,
)
from a2a_research.models import (
    AgentResult,
    AgentRole,
    AgentStatus,
    Claim,
    ResearchSession,
    Verdict,
    WorkflowState,
)


class TestModels:
    def test_research_session_default(self):
        session = ResearchSession(query="Is RAG effective?")
        assert session.id is not None
        assert session.query == "Is RAG effective?"
        assert session.final_report == ""
        assert session.error is None
        assert session.agent_results == {}

    def test_research_session_get_agent_missing(self):
        session = ResearchSession(query="Test")
        result = session.get_agent(AgentRole.RESEARCHER)
        assert result.role == AgentRole.RESEARCHER
        assert result.status == AgentStatus.PENDING

    def test_research_session_get_agent_present(self):
        session = ResearchSession(query="Test")
        session.agent_results[AgentRole.RESEARCHER] = AgentResult(
            role=AgentRole.RESEARCHER,
            status=AgentStatus.COMPLETED,
            message="Done",
        )
        result = session.get_agent(AgentRole.RESEARCHER)
        assert result.status == AgentStatus.COMPLETED

    def test_workflow_state_default(self):
        session = ResearchSession(query="Test")
        state = WorkflowState(session=session)
        assert state.session == session
        assert state.current_agent is None
        assert state.messages == []

    def test_claim_defaults(self):
        claim = Claim(text="RAG reduces hallucinations")
        assert claim.verdict == Verdict.INSUFFICIENT_EVIDENCE
        assert claim.confidence == 0.5
        assert claim.sources == []
        assert claim.evidence_snippets == []

    def test_claim_full(self):
        claim = Claim(
            text="RAG is effective",
            confidence=0.9,
            verdict=Verdict.SUPPORTED,
            sources=["doc_1"],
            evidence_snippets=["Study shows 43% reduction"],
        )
        assert claim.verdict == Verdict.SUPPORTED
        assert claim.confidence == 0.9
        assert claim.sources == ["doc_1"]

    def test_claim_numeric_id_is_coerced_to_string(self) -> None:
        claim = Claim.model_validate({"id": 1, "text": "RAG is effective"})
        assert claim.id == "1"

    def test_claim_blank_id_raises(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            Claim.model_validate({"id": "   ", "text": "x"})

    def test_agent_result_defaults(self):
        result = AgentResult(role=AgentRole.VERIFIER)
        assert result.status == AgentStatus.PENDING
        assert result.message == ""
        assert result.claims == []
        assert result.raw_content == ""
        assert result.citations == []


class TestHelpers:
    def test_create_result(self):
        result = create_result(
            AgentRole.RESEARCHER,
            AgentStatus.COMPLETED,
            "Retrieved docs",
            raw_content="doc1, doc2",
        )
        assert result.role == AgentRole.RESEARCHER
        assert result.status == AgentStatus.COMPLETED
        assert result.message == "Retrieved docs"
        assert result.raw_content == "doc1, doc2"

    def test_format_verdict_supported(self):
        assert format_claim_verdict(Verdict.SUPPORTED) == "✅ SUPPORTED"

    def test_format_verdict_refuted(self):
        assert format_claim_verdict(Verdict.REFUTED) == "❌ REFUTED"

    def test_format_verdict_insufficient(self):
        assert format_claim_verdict(Verdict.INSUFFICIENT_EVIDENCE) == "⚠️  INSUFFICIENT_EVIDENCE"

    def test_format_confidence(self):
        assert format_confidence(0.85) == "85%"
        assert format_confidence(1.0) == "100%"
        assert format_confidence(0.0) == "0%"

    def test_parse_json_safely_with_json(self):
        data = parse_json_safely('{"key": "value", "count": 42}')
        assert data == {"key": "value", "count": 42}

    def test_parse_json_safely_with_fenced_json(self):
        content = '```json\n{"key": "value"}\n```'
        data = parse_json_safely(content)
        assert data == {"key": "value"}

    def test_parse_json_safely_with_markdown(self):
        content = 'Here is the output:\n```json\n{"a": 1}\n```\nend'
        data = parse_json_safely(content)
        assert data == {"a": 1}

    def test_parse_json_safely_invalid(self):
        data = parse_json_safely("not json at all")
        assert data == {}

    def test_parse_json_safely_partial(self):
        content = 'some text before {"partial": true} some text after'
        data = parse_json_safely(content)
        assert data == {"partial": True}

    def test_extract_claims_from_llm_output_valid_json(self):
        raw = (
            '{"verified_claims": ['
            '{"id": "c1", "text": "RAG works", "verdict": "SUPPORTED", '
            '"confidence": 0.9, "sources": ["doc1"], "evidence_snippets": ["evidence"]}]}'
        )
        claims = extract_claims_from_llm_output(raw)
        assert len(claims) == 1
        assert claims[0].text == "RAG works"
        assert claims[0].verdict == Verdict.SUPPORTED
        assert claims[0].confidence == 0.9

    def test_extract_claims_from_llm_output_numeric_id_is_normalized(self) -> None:
        raw = '{"atomic_claims": [{"id": 1, "text": "RAG works", "confidence": 0.9} ]}'
        claims = extract_claims_from_llm_output(raw)
        assert len(claims) == 1
        assert claims[0].id == "1"

    def test_extract_claims_from_llm_output_fallback(self):
        raw = "Some unstructured LLM output that does not contain JSON."
        claims = extract_claims_from_llm_output(raw)
        assert isinstance(claims, list)

    def test_extract_claims_from_llm_output_empty(self):
        claims = extract_claims_from_llm_output("")
        assert claims == []

    def test_aggregate_citations(self):
        session = ResearchSession(query="test")
        session.agent_results[AgentRole.RESEARCHER] = AgentResult(
            role=AgentRole.RESEARCHER, citations=["doc1", "doc2"]
        )
        session.agent_results[AgentRole.VERIFIER] = AgentResult(
            role=AgentRole.VERIFIER, citations=["doc2", "doc3"]
        )
        citations = aggregate_citations(session.agent_results)
        assert citations == ["doc1", "doc2", "doc3"]

    def test_aggregate_citations_empty(self):
        assert aggregate_citations({}) == []

    def test_build_markdown_report(self):
        session = ResearchSession(query="Is RAG effective?")
        session.agent_results[AgentRole.VERIFIER] = AgentResult(
            role=AgentRole.VERIFIER,
            status=AgentStatus.COMPLETED,
            claims=[
                Claim(
                    text="RAG reduces hallucinations",
                    verdict=Verdict.SUPPORTED,
                    confidence=0.85,
                    sources=["rag_accuracy.md"],
                    evidence_snippets=["RAG reduces hallucination rates by up to 43%"],
                ),
                Claim(
                    text="RAG was invented by Facebook",
                    verdict=Verdict.INSUFFICIENT_EVIDENCE,
                    confidence=0.5,
                ),
            ],
        )
        report = build_markdown_report(session)
        assert "# Research Report" in report
        assert "Is RAG effective?" in report
        assert "✅ SUPPORTED" in report
        assert "⚠️  INSUFFICIENT_EVIDENCE" in report
        assert "85%" in report
        assert "**1** claims supported" in report
        assert "**1** inconclusive" in report

    def test_format_claims_section_empty(self):
        result = format_claims_section([])
        assert "No claims" in result


class TestVerdictEnum:
    def test_verdict_values(self):
        assert Verdict.SUPPORTED.value == "SUPPORTED"
        assert Verdict.REFUTED.value == "REFUTED"
        assert Verdict.INSUFFICIENT_EVIDENCE.value == "INSUFFICIENT_EVIDENCE"

    def test_verdict_from_string(self):
        assert Verdict("SUPPORTED") == Verdict.SUPPORTED
        assert Verdict("REFUTED") == Verdict.REFUTED
        assert Verdict("INSUFFICIENT_EVIDENCE") == Verdict.INSUFFICIENT_EVIDENCE


class TestAgentRoleEnum:
    def test_agent_role_values(self):
        assert AgentRole.RESEARCHER.value == "researcher"
        assert AgentRole.ANALYST.value == "analyst"
        assert AgentRole.VERIFIER.value == "verifier"
        assert AgentRole.PRESENTER.value == "presenter"

    def test_all_roles_present(self):
        roles = list(AgentRole)
        assert len(roles) == 4
        assert AgentRole.RESEARCHER in roles
        assert AgentRole.ANALYST in roles
        assert AgentRole.VERIFIER in roles
        assert AgentRole.PRESENTER in roles
