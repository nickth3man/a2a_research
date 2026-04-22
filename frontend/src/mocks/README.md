# mocks/

Mock data for development and testing. Use these when the backend services are unavailable or when writing unit tests.

## Files

| File | Description |
|------|-------------|
| `data.ts` | Mock data definitions: sample research queries, agent responses, and synthesized results |

## Purpose

Mock data lets you develop and demo the UI without hitting live APIs. It also provides predictable fixtures for testing components in different states (empty, loading, error, success).

## Exports

### `AGENTS: Agent[]`

The full list of agents in the research pipeline, each with a `key`, `label`, and pipeline `stage`.

Stages map to the research phases: `ingest`, `plan`, `retrieve`, `verify`, `synthesize`.

### `STAGES: Stage[]`

Pipeline stages in execution order, each with a `key`, `label`, and Roman numeral `n`.

| Key | Label | N |
|-----|-------|---|
| `ingest` | Ingest | I |
| `plan` | Plan | II |
| `retrieve` | Retrieve | III |
| `verify` | Verify | IV |
| `synthesize` | Synthesize | V |

### `MOCK_STATUSES: Record<string, 'pending' | 'running' | 'completed'>`

A realistic snapshot of agent statuses mid-run. Useful for testing the `LoadingState` view.

- Completed: `preprocessor`, `clarifier`, `planner`, `searcher`, `ranker`
- Running: `reader`
- Pending: `deduplicator`, `fact_checker`, `adversary`, `synthesizer`, `critic`, `postprocessor`

### `ALL_DONE: Record<string, 'completed'>`

Every agent marked as `completed`. Use this when you need a fully finished pipeline state.

### `MOCK_METRICS: Record<string, Metric>`

Per-agent metrics for the mid-run snapshot, showing `docs`, `tokens`, and `elapsed` time.

- Docs and tokens vary by agent (e.g., `reader` has 7 docs and 12,840 tokens)
- Pending agents show `0` docs, `0` tokens, and elapsed time `—`

### `TICKER_LINES: string[]`

Example log lines from the `reader` agent. Useful for animating a terminal-style ticker during the loading state.

Lines include actions like `extract`, `fetch`, `score`, `parse`, `filter`, `embed`, and `dispatch`, with offsets, similarity scores, and source filenames.

### `EXAMPLES: string[]`

Pre-canned example research queries for UI demos or quick-fill inputs:

1. "When did the James Webb Space Telescope launch and what is its primary mirror diameter?"
2. "What are the main differences between the A2A protocol and MCP?"
3. "What year was the transformer architecture paper published, and who are its authors?"

### `MOCK_REPORT: string`

A full synthesized markdown report about the James Webb Space Telescope. It covers:

- Launch date (December 25, 2021) and vehicle (Ariane 5)
- Primary mirror specs (6.5 metres, 18 segments)
- Key mission objectives
- Orbit location (Sun-Earth L2 Lagrange point)

Includes inline source citations like `[1,3]`.

### `MOCK_CLAIMS: Claim[]`

Fact-checking claims extracted from the mock report, each with:

- `text`: the claim text
- `verdict`: `SUPPORTED` or `REFUTED`
- `confidence`: 0.0 – 1.0 score
- `sources`: list of source filenames
- `evidence`: optional refutation detail

| Claim | Verdict | Confidence |
|-------|---------|------------|
| JWST launched December 25, 2021 on Ariane 5 | SUPPORTED | 0.98 |
| Primary mirror is 6.5 metres across 18 segments | SUPPORTED | 0.96 |
| JWST orbits at Sun-Earth L2, 1.5 million km away | SUPPORTED | 0.94 |
| JWST has 10× the light-collecting area of Hubble | REFUTED | 0.91 |

The last claim includes `evidence` correcting the ratio to approximately 6×.

### `MOCK_SOURCES: Source[]`

Bibliographic entries for the report, each with:

- `file`: source filename
- `title`: full document title
- `meta`: publication or institutional metadata

| File | Title | Meta |
|------|-------|------|
| `nasa_jwst_overview.pdf` | James Webb Space Telescope Mission Overview | NASA Technical Report · 2022 |
| `webb_telescope_mission.pdf` | JWST Science Instruments and Mission Architecture | Space Telescope Science Institute |
| `esa_launch_report.pdf` | Ariane 5 VA256 Launch Campaign Report | ESA · January 2022 |
| `exoplanet_atmosphere_guide.pdf` | Spectroscopic Analysis with JWST NIRSpec | Astrophysical Journal · 2023 |

## Usage Example

```tsx
import { mockResearchResult } from "../mocks/data";

// During development
<ResultsState result={mockResearchResult} />
```

## Keeping Mocks Current

Update `data.ts` whenever the API response shape changes so tests and Storybook stories stay accurate.
