import { useMemo } from 'react';
import { Logo } from './Logo';
import type { UIState } from '../types';

interface MastheadProps {
  uiState: UIState;
}

export function Masthead({ uiState }: MastheadProps) {
  const now = useMemo(
    () =>
      new Date().toLocaleString('en-US', {
        month: 'short',
        day: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
      }),
    []
  );

  const stateLabel = uiState === 'empty' ? 'idle' : uiState === 'loading' ? 'running' : 'complete';
  const stateColor = uiState === 'empty' ? 'var(--muted)' : uiState === 'loading' ? 'var(--amber)' : 'var(--emerald)';

  return (
    <div style={{ borderBottom: '1px solid var(--rule)', background: 'var(--ivory)' }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '22px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 24 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 6 }}>
              <Logo />
              <span
                className="mono"
                style={{
                  fontSize: 10.5,
                  letterSpacing: '.22em',
                  color: 'var(--muted)',
                  textTransform: 'uppercase',
                }}
              >
                A2A / Vol. 01 · No. 042
              </span>
            </div>
            <h1
              className="serif"
              style={{
                fontSize: 52,
                lineHeight: 1,
                letterSpacing: '-0.025em',
                color: 'var(--ink)',
                marginTop: 2,
              }}
            >
              The Research <em style={{ color: 'var(--accent)' }}>Pipeline</em>
            </h1>
            <div style={{ marginTop: 10, fontSize: 13, color: 'var(--muted)', maxWidth: 560 }}>
              Twelve agents, five stages. Retrieval, verification, synthesis — end to end.
            </div>
          </div>
          <div style={{ textAlign: 'right', paddingTop: 4 }}>
            <div
              className="mono"
              style={{
                fontSize: 10.5,
                letterSpacing: '.15em',
                textTransform: 'uppercase',
                color: 'var(--muted)',
              }}
            >
              {now}
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, justifyContent: 'flex-end', marginTop: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: stateColor,
                  animation: uiState === 'loading' ? 'pulse-ring-amber 1.6s ease-out infinite' : 'none',
                }}
              />
              <span className="mono" style={{ fontSize: 11, color: 'var(--ink-soft)', letterSpacing: '.08em' }}>
                status: <strong style={{ color: stateColor }}>{stateLabel}</strong>
              </span>
            </div>
          </div>
        </div>
      </div>
      {/* double rule */}
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 28px' }}>
        <div style={{ height: 1, background: 'var(--ink)' }} />
        <div style={{ height: 2 }} />
        <div style={{ height: 1, background: 'var(--ink)' }} />
      </div>
    </div>
  );
}
