# LLM

Shared LLM provider layer for the backend.

## Runtime role

This package provides the single chat-model implementation used by the backend. It wraps an OpenAI-compatible client, logs request lifecycle events, normalizes provider failures, and exposes helpers for structured output parsing and singleton access.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Re-exports the public LLM API |
| `providers.py` | OpenRouter-backed chat client, errors, and helpers |

## Public API

Exported from `a2a_research.backend.llm`:

- `OpenRouterChatModel` — async chat client
- `ChatResponse` — response wrapper with content and usage metadata
- `ProviderRequestError` — base upstream provider failure
- `ProviderRateLimitError` — transient rate-limit failure
- `get_llm()` — returns the cached model instance
- `reset_provider_singletons()` — clears cached provider state
- `parse_structured_response()` — validates JSON output into a Pydantic model

## Provider setup

`OpenRouterChatModel` reads defaults from `a2a_research.backend.core.settings.settings.llm` unless explicit overrides are passed to the constructor.

It uses:

- `settings.llm.model` for the model name
- `settings.llm.api_key` for authentication
- `settings.llm.base_url` for the OpenAI-compatible endpoint

If no API key is available, requests fail immediately with `ProviderRequestError`.

## Client behavior

`OpenRouterChatModel.ainvoke(messages)`:

- creates the underlying `AsyncOpenAI` client lazily
- sends `chat.completions.create(...)` with `temperature=0.3`
- logs request start, success, and failure
- returns `ChatResponse` with:
  - `content`
  - `prompt_tokens`
  - `completion_tokens`
  - `finish_reason`
  - `model`

Provider exceptions are converted into:

- `ProviderRateLimitError` for HTTP 429 / rate-limit errors
- `ProviderRequestError` for all other failures

## Structured output helper

`parse_structured_response(content, schema)`:

- parses content as JSON using the shared JSON utility
- validates the result with `schema.model_validate(...)`
- returns `None` when parsing or validation fails

## Singleton helper

`get_llm()` returns a cached `OpenRouterChatModel` instance.

`reset_provider_singletons()` clears that cache for tests or reconfiguration.
