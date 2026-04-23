"""Agent endpoint configuration mixin (ports and URLs)."""

from __future__ import annotations

from pydantic import Field, field_validator


def _normalize_agent_url(url: str) -> str:
    """Ensure mounted agent URLs always target the canonical trailing-slash path."""

    return url.rstrip("/") + "/"


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
        default="http://localhost:8000/agents/preprocessor/",
        description="Preprocessor HTTP A2A URL.",
    )
    clarifier_url: str = Field(
        default="http://localhost:8000/agents/clarifier/",
        description="Clarifier HTTP A2A URL.",
    )
    planner_url: str = Field(
        default="http://localhost:8000/agents/planner/",
        description="Planner HTTP A2A URL.",
    )
    searcher_url: str = Field(
        default="http://localhost:8000/agents/searcher/",
        description="Searcher HTTP A2A URL.",
    )
    ranker_url: str = Field(
        default="http://localhost:8000/agents/ranker/",
        description="Ranker HTTP A2A URL.",
    )
    reader_url: str = Field(
        default="http://localhost:8000/agents/reader/",
        description="Reader HTTP A2A URL.",
    )
    evidence_deduplicator_url: str = Field(
        default="http://localhost:8000/agents/evidence-deduplicator/",
        description="EvidenceDeduplicator HTTP A2A URL.",
    )
    fact_checker_url: str = Field(
        default="http://localhost:8000/agents/fact-checker/",
        description="FactChecker HTTP A2A URL.",
    )
    adversary_url: str = Field(
        default="http://localhost:8000/agents/adversary/",
        description="Adversary HTTP A2A URL.",
    )
    synthesizer_url: str = Field(
        default="http://localhost:8000/agents/synthesizer/",
        description="Synthesizer HTTP A2A URL.",
    )
    critic_url: str = Field(
        default="http://localhost:8000/agents/critic/",
        description="Critic HTTP A2A URL.",
    )
    postprocessor_url: str = Field(
        default="http://localhost:8000/agents/postprocessor/",
        description="Postprocessor HTTP A2A URL.",
    )

    @field_validator(
        "preprocessor_url",
        "clarifier_url",
        "planner_url",
        "searcher_url",
        "ranker_url",
        "reader_url",
        "evidence_deduplicator_url",
        "fact_checker_url",
        "adversary_url",
        "synthesizer_url",
        "critic_url",
        "postprocessor_url",
        mode="before",
    )
    @classmethod
    def normalize_agent_urls(cls, value: str) -> str:
        return _normalize_agent_url(value)
