"""Fact checker payload helpers."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from core import Claim, WebSource, get_data_part, get_text_part
from tools import PageContent

if TYPE_CHECKING:
    from a2a.server.agent_execution import RequestContext


def _extract_payload(context: RequestContext) -> dict[str, Any]:
    if context.message is None:
        return {}
    for part in context.message.parts:
        data_part = get_data_part(part)
        if isinstance(data_part, dict):
            return data_part
        text_part = get_text_part(part)
        if text_part:
            try:
                data = json.loads(text_part)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                return data
    return {}


def _coerce_claims(raw: Any) -> list[Claim]:
    claims: list[Claim] = []
    for item in raw or []:
        if isinstance(item, Claim):
            claims.append(item)
            continue
        if isinstance(item, dict):
            try:
                claims.append(Claim.model_validate(item))
            except ValidationError:
                continue
    return claims


def _coerce_pages(raw: Any) -> list[PageContent]:
    pages: list[PageContent] = []
    for item in raw or []:
        if isinstance(item, PageContent):
            pages.append(item)
            continue
        if isinstance(item, dict):
            try:
                pages.append(PageContent.model_validate(item))
            except ValidationError:
                continue
    return pages


def _coerce_sources(raw: Any) -> list[WebSource]:
    sources: list[WebSource] = []
    for item in raw or []:
        if isinstance(item, WebSource):
            sources.append(item)
            continue
        if isinstance(item, dict):
            try:
                sources.append(WebSource.model_validate(item))
            except ValidationError:
                continue
    return sources
