"""Request and response models for the FastAPI gateway."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)

    @field_validator("query")
    @classmethod
    def normalize_query(cls, value: str) -> str:
        query = value.strip()
        if not query:
            raise ValueError("Query must not be blank")
        return query


class ResearchResponse(BaseModel):
    session_id: str
