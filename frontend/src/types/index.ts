export type UIState = 'empty' | 'loading' | 'results';

export type AgentStatus = 'pending' | 'running' | 'completed' | 'warning' | 'degraded';

export interface Agent {
  key: string;
  label: string;
  stage: string;
}

export interface Stage {
  key: string;
  label: string;
  n: string;
}

export interface Metric {
  docs: number;
  tokens: number;
  elapsed: string;
}

export type Verdict = 'SUPPORTED' | 'REFUTED' | 'UNVERIFIABLE';

export interface Claim {
  text: string;
  verdict: Verdict;
  confidence: number;
  sources: string[];
  evidence?: string;
}

export interface Source {
  file: string;
  title: string;
  meta: string;
}

export type StatusMap = Record<string, AgentStatus>;

export interface DiagnosticItem {
  role: string | null;
  code: string;
  severity: 'fatal' | 'warning' | 'degraded';
  retryable: boolean;
  root_cause: string;
  remediation: string;
  trace_id?: string;
}
