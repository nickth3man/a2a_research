"""Agent mount helpers for the FastAPI gateway."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def mount_agents(app: FastAPI) -> None:
    """Mount each agent's Starlette ASGI app under /agents/<name>.

    Imports are deferred to avoid loading heavy agent dependencies during
    test collection of unrelated tests.
    """
    from agents.langgraph.fact_checker.main import (
        FactCheckerExecutor,
    )
    from agents.langgraph.fact_checker.main import (
        build_http_app as build_fact_checker_app,
    )
    from agents.pocketflow.clarifier.main import (
        ClarifierExecutor,
    )
    from agents.pocketflow.clarifier.main import (
        build_http_app as build_clarifier_app,
    )
    from agents.pocketflow.planner.main import (
        PlannerExecutor,
    )
    from agents.pocketflow.planner.main import (
        build_http_app as build_planner_app,
    )
    from agents.pydantic_ai.synthesizer.main import (
        SynthesizerExecutor,
    )
    from agents.pydantic_ai.synthesizer.main import (
        build_http_app as build_synthesizer_app,
    )
    from agents.smolagents.reader.main import (
        ReaderExecutor,
    )
    from agents.smolagents.reader.main import (
        build_http_app as build_reader_app,
    )
    from agents.smolagents.searcher.main import (
        SearcherExecutor,
    )
    from agents.smolagents.searcher.main import (
        build_http_app as build_searcher_app,
    )
    from agents.stubs.adversary.main import (
        AdversaryExecutor,
    )
    from agents.stubs.adversary.main import (
        build_http_app as build_adversary_app,
    )
    from agents.stubs.critic.main import (
        CriticExecutor,
    )
    from agents.stubs.critic.main import (
        build_http_app as build_critic_app,
    )
    from agents.stubs.evidence_deduplicator.main import (
        EvidenceDeduplicatorExecutor,
    )
    from agents.stubs.evidence_deduplicator.main import (
        build_http_app as build_evidence_deduplicator_app,
    )
    from agents.stubs.postprocessor.main import (
        PostprocessorExecutor,
    )
    from agents.stubs.postprocessor.main import (
        build_http_app as build_postprocessor_app,
    )
    from agents.stubs.preprocessor.main import (
        PreprocessorExecutor,
    )
    from agents.stubs.preprocessor.main import (
        build_http_app as build_preprocessor_app,
    )
    from agents.stubs.ranker.main import (
        RankerExecutor,
    )
    from agents.stubs.ranker.main import (
        build_http_app as build_ranker_app,
    )
    from core import AgentRole, get_registry

    registry = get_registry()
    registry.register_executor(AgentRole.PREPROCESSOR, PreprocessorExecutor())
    registry.register_executor(AgentRole.CLARIFIER, ClarifierExecutor())
    registry.register_executor(AgentRole.PLANNER, PlannerExecutor())
    registry.register_executor(AgentRole.SEARCHER, SearcherExecutor())
    registry.register_executor(AgentRole.RANKER, RankerExecutor())
    registry.register_executor(AgentRole.READER, ReaderExecutor())
    registry.register_executor(
        AgentRole.EVIDENCE_DEDUPLICATOR,
        EvidenceDeduplicatorExecutor(),
    )
    registry.register_executor(AgentRole.FACT_CHECKER, FactCheckerExecutor())
    registry.register_executor(AgentRole.ADVERSARY, AdversaryExecutor())
    registry.register_executor(AgentRole.SYNTHESIZER, SynthesizerExecutor())
    registry.register_executor(AgentRole.CRITIC, CriticExecutor())
    registry.register_executor(
        AgentRole.POSTPROCESSOR, PostprocessorExecutor()
    )

    app.mount(
        "/agents/preprocessor",
        build_preprocessor_app(),  # type: ignore[no-untyped-call]
    )
    app.mount(
        "/agents/clarifier",
        build_clarifier_app(),
    )
    app.mount(
        "/agents/planner",
        build_planner_app(),
    )
    app.mount(
        "/agents/searcher",
        build_searcher_app(),
    )
    app.mount(
        "/agents/ranker",
        build_ranker_app(),  # type: ignore[no-untyped-call]
    )
    app.mount(
        "/agents/reader",
        build_reader_app(),
    )
    app.mount(
        "/agents/evidence-deduplicator",
        build_evidence_deduplicator_app(),  # type: ignore[no-untyped-call]
    )
    app.mount(
        "/agents/fact-checker",
        build_fact_checker_app(),
    )
    app.mount(
        "/agents/adversary",
        build_adversary_app(),  # type: ignore[no-untyped-call]
    )
    app.mount(
        "/agents/synthesizer",
        build_synthesizer_app(),
    )
    app.mount(
        "/agents/critic",
        build_critic_app(),  # type: ignore[no-untyped-call]
    )
    app.mount(
        "/agents/postprocessor",
        build_postprocessor_app(),  # type: ignore[no-untyped-call]
    )
