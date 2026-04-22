# Tools

Web research utilities used by the Searcher and Reader agents.

## Public API

The package exports these symbols from `__init__.py`:

- `web_search`
- `fetch_and_extract`
- `fetch_many`
- `WebHit`
- `SearchResult`
- `PageContent`

## Module Guide

| File | Purpose |
|------|---------|
| `search.py` | Parallel search orchestration over all providers |
| `search_brave.py` | Brave Search API client |
| `search_ddg.py` | DuckDuckGo search client |
| `search_tavily.py` | Tavily search client |
| `search_merge.py` | Merge/dedupe hits that share the same URL |
| `search_models.py` | Pydantic models for search results |
| `search_providers.py` | Re-exports provider functions |
| `fetch.py` | URL fetch + markdown extraction |

## Search Flow

`web_search()` runs Tavily, Brave, and DuckDuckGo concurrently.

1. `search.py` picks the result cap from the call or from settings.
2. Each provider returns `(hits, error)` instead of raising.
3. `search_merge.merge_hits_by_url()` combines duplicate URLs.
4. `SearchResult` records merged hits, provider errors, and which providers succeeded.

### Provider behavior

- **Tavily**: uses `AsyncTavilyClient`, requests `search_depth="basic"`, and maps `results` into `WebHit` objects.
- **Brave**: uses the Brave Web Search API, applies client throttling, retries on HTTP 429, and maps `web.results` into `WebHit` objects.
- **DuckDuckGo**: uses `ddgs.DDGS().text(...)` in a worker thread and maps `href`/`url` fields into `WebHit` objects.

## Fetch Flow

`fetch.py` fetches one or many URLs and extracts main text with `trafilatura`.

- `fetch_and_extract()` wraps the sync fetch/extract work in `asyncio.to_thread()`.
- `fetch_many()` fan-outs across URLs with `asyncio.gather()`.
- `PageContent` includes `url`, `title`, `markdown`, `word_count`, and `error`.

## Data Models

### `WebHit`

Represents a single search result.

- `url`
- `title`
- `snippet`
- `source` — provider id or merged provider ids
- `score` — normalized float from `0.0` to `1.0`

### `SearchResult`

Represents one search request.

- `hits`
- `errors`
- `providers_attempted`
- `providers_successful`
- `any_provider_succeeded`

### `PageContent`

Represents extracted page content.

- `url`
- `title`
- `markdown`
- `word_count`
- `error`

## Merging Rules

`merge_hits_by_url()` merges hits with the same URL by:

- combining unique snippets with `\n---\n`
- keeping the longest title
- keeping the highest score
- sorting and deduplicating provider ids in `source`

## Settings and Dependencies

The search providers rely on application settings for API keys and limits:

- `settings.tavily_api_key`
- `settings.brave_api_key`
- `settings.search_max_results`

`fetch.py` depends on `trafilatura` at runtime.

## Notes

- Search failures are reported in `SearchResult.errors`; `web_search()` does not raise on provider failure.
- Brave includes rate-limit logging and retry delay handling.
- DuckDuckGo runs in a thread because the client call is synchronous.
