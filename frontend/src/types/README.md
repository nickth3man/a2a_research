# types/
Central TypeScript type definitions for the frontend application.

## Files

| File | Description |
|------|-------------|
| `index.ts` | Shared types, interfaces, and type aliases used across components and hooks |

## Types Reference

### `UIState`
Union type representing the top-level UI state.

```ts
'empty' | 'loading' | 'results'
```

### `AgentStatus`
Union type representing the execution status of a pipeline agent.

```ts
'pending' | 'running' | 'completed'
```

### `Agent`
Describes a single agent in the pipeline.

| Property | Type | Description |
|----------|------|-------------|
| `key` | `string` | Unique identifier for the agent |
| `label` | `string` | Human-readable display name |
| `stage` | `string` | Current pipeline stage key |

### `Stage`
Describes a pipeline stage.

| Property | Type | Description |
|----------|------|-------------|
| `key` | `string` | Unique identifier for the stage |
| `label` | `string` | Human-readable display name |
| `n` | `string` | Stage number or order index |

### `Metric`
Aggregated metrics for a completed research run.

| Property | Type | Description |
|----------|------|-------------|
| `docs` | `number` | Number of documents processed |
| `tokens` | `number` | Number of tokens consumed |
| `elapsed` | `string` | Human-readable elapsed time |

### `Verdict`
Fact-check verdict for a claim.

```ts
'SUPPORTED' | 'REFUTED' | 'UNVERIFIABLE'
```

### `Claim`
A single claim extracted during fact-checking.

| Property | Type | Description |
|----------|------|-------------|
| `text` | `string` | The claim text |
| `verdict` | `Verdict` | Fact-check result |
| `confidence` | `number` | Confidence score (0-1) |
| `sources` | `string[]` | Supporting source identifiers |
| `evidence` | `string` | *(optional)* Supporting evidence text |

### `Source`
A source document referenced by the pipeline.

| Property | Type | Description |
|----------|------|-------------|
| `file` | `string` | Source file name or path |
| `title` | `string` | Document title |
| `meta` | `string` | Additional metadata |

### `StatusMap`
A mapping from agent keys to their current status.

```ts
Record<string, AgentStatus>
```

## Usage Example

```tsx
import type { Agent, Claim, UIState } from '../types';

interface Props {
  agents: Agent[];
  claims: Claim[];
  uiState: UIState;
}
```

## Notes

If the type surface grows, consider splitting into focused files (for example, `agent.ts`, `api.ts`) and re-exporting them from `index.ts`.

