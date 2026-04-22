import type { Agent, Stage, Metric, Claim, Source } from '../types';

export const AGENTS: Agent[] = [
  { key: 'preprocessor',  label: 'Preprocessor',  stage: 'ingest' },
  { key: 'clarifier',     label: 'Clarifier',     stage: 'ingest' },
  { key: 'planner',       label: 'Planner',       stage: 'plan' },
  { key: 'searcher',      label: 'Searcher',      stage: 'retrieve' },
  { key: 'ranker',        label: 'Ranker',        stage: 'retrieve' },
  { key: 'reader',        label: 'Reader',        stage: 'retrieve' },
  { key: 'deduplicator',  label: 'Deduplicator',  stage: 'retrieve' },
  { key: 'fact_checker',  label: 'Fact Checker',  stage: 'verify' },
  { key: 'adversary',     label: 'Adversary',     stage: 'verify' },
  { key: 'synthesizer',   label: 'Synthesizer',   stage: 'synthesize' },
  { key: 'critic',        label: 'Critic',        stage: 'synthesize' },
  { key: 'postprocessor', label: 'Postprocessor', stage: 'synthesize' },
];

export const STAGES: Stage[] = [
  { key: 'ingest',     label: 'Ingest',     n: 'I' },
  { key: 'plan',       label: 'Plan',       n: 'II' },
  { key: 'retrieve',   label: 'Retrieve',   n: 'III' },
  { key: 'verify',     label: 'Verify',     n: 'IV' },
  { key: 'synthesize', label: 'Synthesize', n: 'V' },
];

export const MOCK_STATUSES: Record<string, 'pending' | 'running' | 'completed'> = {
  preprocessor: 'completed',
  clarifier: 'completed',
  planner: 'completed',
  searcher: 'completed',
  ranker: 'completed',
  reader: 'running',
  deduplicator: 'pending',
  fact_checker: 'pending',
  adversary: 'pending',
  synthesizer: 'pending',
  critic: 'pending',
  postprocessor: 'pending',
};

export const ALL_DONE: Record<string, 'completed'> = Object.fromEntries(
  AGENTS.map((a) => [a.key, 'completed'])
);

export const MOCK_METRICS: Record<string, Metric> = {
  preprocessor:  { docs: 1,  tokens: 412,   elapsed: '0.3s' },
  clarifier:     { docs: 1,  tokens: 238,   elapsed: '0.5s' },
  planner:       { docs: 1,  tokens: 1284,  elapsed: '1.2s' },
  searcher:      { docs: 24, tokens: 3102,  elapsed: '3.8s' },
  ranker:        { docs: 24, tokens: 1876,  elapsed: '1.4s' },
  reader:        { docs: 7,  tokens: 12840, elapsed: '8.2s' },
  deduplicator:  { docs: 0,  tokens: 0,     elapsed: '—' },
  fact_checker:  { docs: 0,  tokens: 0,     elapsed: '—' },
  adversary:     { docs: 0,  tokens: 0,     elapsed: '—' },
  synthesizer:   { docs: 0,  tokens: 0,     elapsed: '—' },
  critic:        { docs: 0,  tokens: 0,     elapsed: '—' },
  postprocessor: { docs: 0,  tokens: 0,     elapsed: '—' },
};

export const TICKER_LINES = [
  'reader.extract  → passage @ offset 2431, sim 0.81',
  'reader.fetch    → webb_telescope_mission.pdf §4.2',
  'reader.score    → chunk[07/12] cosine=0.724',
  'reader.parse    → nasa_jwst_overview.pdf',
  'reader.filter   → dropping 3 below threshold',
  'reader.embed    → generating vectors, dim=1536',
  'reader.dispatch → sending to deduplicator queue',
  'reader.extract  → passage @ offset 8012, sim 0.79',
];

export const EXAMPLES = [
  'When did the James Webb Space Telescope launch and what is its primary mirror diameter?',
  'What are the main differences between the A2A protocol and MCP?',
  'What year was the transformer architecture paper published, and who are its authors?',
];

export const MOCK_REPORT = `## James Webb Space Telescope — Mission Overview

The **James Webb Space Telescope (JWST)** launched on **December 25, 2021**, aboard an Ariane 5 rocket from the Guiana Space Centre in Kourou, French Guiana.[1,3]

### Primary Mirror

JWST features a segmented primary mirror with a total diameter of **6.5 metres** (21 ft), composed of 18 hexagonal gold-plated beryllium segments.[2] This gives JWST roughly **6× the light-collecting area** of the Hubble Space Telescope.[2]

### Key Mission Objectives

- Observe the first galaxies to form in the early universe[1]
- Study star and planetary system formation
- Investigate the potential for life in exoplanet atmospheres[4]
- Perform solar system science complementing other missions

### Orbit & Operations

JWST orbits the **Sun-Earth L2 Lagrange point**, approximately 1.5 million km from Earth.[1] The location provides a stable thermal environment and continuous observation capability.`;

export const MOCK_CLAIMS: Claim[] = [
  { text: 'JWST launched on December 25, 2021 aboard an Ariane 5 rocket.', verdict: 'SUPPORTED', confidence: 0.98, sources: ['nasa_jwst_overview.pdf', 'esa_launch_report.pdf'] },
  { text: 'The primary mirror diameter is 6.5 metres across 18 beryllium segments.', verdict: 'SUPPORTED', confidence: 0.96, sources: ['webb_telescope_mission.pdf'] },
  { text: 'JWST orbits at the Sun-Earth L2 point, 1.5 million km from Earth.', verdict: 'SUPPORTED', confidence: 0.94, sources: ['nasa_jwst_overview.pdf'] },
  { text: 'JWST has 10× the light-collecting area of Hubble.', verdict: 'REFUTED', confidence: 0.91, sources: ['webb_telescope_mission.pdf'], evidence: 'Actual ratio is approximately 6×, not 10×.' },
];

export const MOCK_SOURCES: Source[] = [
  { file: 'nasa_jwst_overview.pdf',         title: 'James Webb Space Telescope Mission Overview',         meta: 'NASA Technical Report · 2022' },
  { file: 'webb_telescope_mission.pdf',     title: 'JWST Science Instruments and Mission Architecture',   meta: 'Space Telescope Science Institute' },
  { file: 'esa_launch_report.pdf',          title: 'Ariane 5 VA256 Launch Campaign Report',               meta: 'ESA · January 2022' },
  { file: 'exoplanet_atmosphere_guide.pdf', title: 'Spectroscopic Analysis with JWST NIRSpec',            meta: 'Astrophysical Journal · 2023' },
];
