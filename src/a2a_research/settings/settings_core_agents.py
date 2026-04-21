"""Agent endpoint configuration mixin (ports and URLs)."""

from __future__ import annotations

from pydantic import Field


class AgentEndpointsMixin:
    """Mixin providing agent HTTP A2A port and URL fields."""

    preprocessor_port: int = Field(
        default=10006, description="Preprocessor HTTP A2A port."
    )
    clarifier_port: int = Field(
        default=10007, description="Clarifier HTTP A2A port."
    )
    planner_port: int = Field(
        default=10001, description="Planner HTTP A2A port."
    )
    searcher_port: int = Field(
        default=10002, description="Searcher HTTP A2A port."
    )
    ranker_port: int = Field(
        default=10008, description="Ranker HTTP A2A port."
    )
    reader_port: int = Field(
        default=10003, description="Reader HTTP A2A port."
    )
    evidence_deduplicator_port: int = Field(
        default=10009,
        description="EvidenceDeduplicator HTTP A2A port.",
    )
    fact_checker_port: int = Field(
        default=10004, description="FactChecker HTTP A2A port."
    )
    adversary_port: int = Field(
        default=10010, description="Adversary HTTP A2A port."
    )
    synthesizer_port: int = Field(
        default=10005, description="Synthesizer HTTP A2A port."
    )
    critic_port: int = Field(
        default=10011, description="Critic HTTP A2A port."
    )
    postprocessor_port: int = Field(
        default=10012, description="Postprocessor HTTP A2A port."
    )
    preprocessor_url: str = Field(
        default="http://localhost:10006",
        description="Preprocessor HTTP A2A URL.",
    )
    clarifier_url: str = Field(
        default="http://localhost:10007",
        description="Clarifier HTTP A2A URL.",
    )
    planner_url: str = Field(
        default="http://localhost:10001",
        description="Planner HTTP A2A URL.",
    )
    searcher_url: str = Field(
        default="http://localhost:10002",
        description="Searcher HTTP A2A URL.",
    )
    ranker_url: str = Field(
        default="http://localhost:10008",
        description="Ranker HTTP A2A URL.",
    )
    reader_url: str = Field(
        default="http://localhost:10003",
        description="Reader HTTP A2A URL.",
    )
    evidence_deduplicator_url: str = Field(
        default="http://localhost:10009",
        description="EvidenceDeduplicator HTTP A2A URL.",
    )
    fact_checker_url: str = Field(
        default="http://localhost:10004",
        description="FactChecker HTTP A2A URL.",
    )
    adversary_url: str = Field(
        default="http://localhost:10010",
        description="Adversary HTTP A2A URL.",
    )
    synthesizer_url: str = Field(
        default="http://localhost:10005",
        description="Synthesizer HTTP A2A URL.",
    )
    critic_url: str = Field(
        default="http://localhost:10011",
        description="Critic HTTP A2A URL.",
    )
    postprocessor_url: str = Field(
        default="http://localhost:10012",
        description="Postprocessor HTTP A2A URL.",
    )
