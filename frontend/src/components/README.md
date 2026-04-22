# components/

React UI components for the A2A research frontend. Each file exports one or more named functional components written in TypeScript.

## Directory Role

This directory contains the visual building blocks of the application. Components are organized as self-contained files that compose together in `App.tsx` to render the full interface. Shared layout primitives live in `Primitives.tsx` so other components can stay consistent without duplicating styles.

## Components

| Component | File | Description |
|-----------|------|-------------|
| `EmptyState` | `EmptyState.tsx` | Landing placeholder shown before a query is submitted. Features an animated typing effect for a sample query, a decorative SVG watermark, and summary stats (agents, stages, docs indexed, latency). |
| `HowItWorks` | `HowItWorks.tsx` | Four-step explainer (Query, Retrieve, Verify, Synthesize) displayed as a horizontal grid with Roman numerals and vertical dividers. |
| `LoadingState` | `LoadingState.tsx` | Active research state. Composed of four sub-views: a circular progress indicator with stage stepper, an SVG DAG visualization of the 12-agent pipeline, a terminal-style live ticker, and an agent roster grid. |
| `Logo` | `Logo.tsx` | 36 x 36 SVG brand mark with orbiting circles animated via SMIL. |
| `Masthead` | `Masthead.tsx` | Top header bar containing the Logo, publication-style title, current timestamp, and a status indicator dot (idle, running, or complete). |
| `Primitives` | `Primitives.tsx` | Shared layout primitives: `Paper` (card container), `Eyebrow` (small label with optional dot), and `Rule` (horizontal divider with optional label). |
| `QueryInput` | `QueryInput.tsx` | Primary input for research questions. Includes a textarea, example-query chips, character counter, keyboard-shortcut hint, and a submit button with loading state. |
| `ResultsState` | `ResultsState.tsx` | Final output view. Shows a stats strip, a rendered markdown report with inline citation badges, a claims list with verdicts and confidence bars, and a numbered sources panel. |
| `StateNav` | `StateNav.tsx` | Segmented control that lets the user switch between the three top-level UI states: Idle, Running, and Complete. |

## Internal Sub-components

Some files define helper components that are not exported but are worth noting:

| Sub-component | Parent | Purpose |
|---------------|--------|---------|
| `PipelineFlow` | `LoadingState.tsx` | SVG graph that draws agents as nodes, stages as dashed columns, and edges as animated Bézier curves colored by status. |
| `LiveTicker` | `LoadingState.tsx` | Dark terminal pane with CRT scanlines that cycles through mock agent log lines with timestamps. |
| `BigProgress` | `LoadingState.tsx` | Circular progress ring with radial tick marks, percentage count-up, and a stage micro-stepper bar. |
| `AgentRoster` | `LoadingState.tsx` | Two-column grid of agent cards showing status dot, token count, and elapsed time. |
| `SummaryStrip` | `ResultsState.tsx` | Horizontal stats bar (sources, claims verified, confidence, elapsed time). |
| `ReportCard` | `ResultsState.tsx` | Renders a mock markdown report with headings, bullet points, bold text, and clickable citation superscripts. |
| `ClaimRow` | `ResultsState.tsx` | Individual claim card with a verdict badge, confidence bar, source list, and optional evidence block. |
| `ConfidenceBar` | `ResultsState.tsx` | Animated horizontal bar that fills to a claim's confidence percentage. |
| `StatBlock` | `ResultsState.tsx` | Reusable stat cell used by `SummaryStrip` with optional count-up animation. |

## Conventions

- File names match the primary exported component (PascalCase).
- Components are functional and use hooks for state and effects.
- Import shared visual primitives from `Primitives.tsx` instead of inlining card or label styles.
- Mock data and custom hooks are imported from sibling `../mocks/` and `../hooks/` directories.

## Dependencies within this directory

- `EmptyState.tsx`, `LoadingState.tsx`, `QueryInput.tsx`, `ResultsState.tsx` all import from `Primitives.tsx`.
- `Masthead.tsx` imports `Logo.tsx`.
- `LoadingState.tsx` and `ResultsState.tsx` import custom hooks (`useCountUp`, `useTicker`, `useTyping`) and mock data.
