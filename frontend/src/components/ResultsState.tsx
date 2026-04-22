import { useState, useEffect } from 'react';
import { Paper, Eyebrow } from './Primitives';
import { useCountUp } from '../hooks/useCountUp';
import type { Claim, Source, Verdict } from '../types';

function renderWithCitations(text: string) {
  const parts = text.split(/(\[\d+(?:\s*,\s*\d+)*\])/g);
  return parts.map((p, i) => {
    const m = p.match(/^\[(\d+(?:\s*,\s*\d+)*)\]$/);
    if (!m) return p;
    return m[1]
      .split(',')
      .map((n) => n.trim())
      .map((n, j) => (
        <sup
          key={`${i}-${j}`}
          style={{
            display: 'inline-block',
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 9.5,
            fontWeight: 700,
            color: 'var(--accent)',
            background: 'var(--accent-soft)',
            border: '1px solid #c8d1ff',
            borderRadius: 2,
            padding: '0 4px',
            marginLeft: j === 0 ? 3 : 1,
            marginRight: 1,
            lineHeight: '14px',
            verticalAlign: 'super',
            cursor: 'pointer',
          }}
        >
          {n}
        </sup>
      ));
  });
}

function StatBlock({
  label,
  value,
  sub,
  accent,
  delay = 0,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: string;
  delay?: number;
}) {
  const numeric = typeof value === 'number';
  const n = useCountUp(numeric ? value : 0, 1000, []);

  return (
    <div
      className="reveal"
      style={{
        animationDelay: `${delay}s`,
        padding: '20px 22px',
        borderRight: '1px solid var(--rule)',
        minWidth: 0,
      }}
    >
      <div className="eyebrow" style={{ marginBottom: 10 }}>
        {label}
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
        <span
          className="serif"
          style={{
            fontSize: 40,
            lineHeight: 1,
            letterSpacing: '-0.025em',
            color: accent || 'var(--ink)',
          }}
        >
          {numeric ? n : value}
        </span>
        {sub && <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', letterSpacing: '.08em' }}>{sub}</span>}
      </div>
    </div>
  );
}

function SummaryStrip({ claims, sources }: { claims: Claim[]; sources: Source[] }) {
  const supported = claims.filter((c) => c.verdict === 'SUPPORTED').length;
  const avgConf = claims.length
    ? Math.round((claims.reduce((a, c) => a + c.confidence, 0) / claims.length) * 100) + '%'
    : '—';
  return (
    <Paper className="reveal reveal-1" style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', padding: 0, overflow: 'hidden' }}>
      <StatBlock label="Sources consulted" value={sources.length} delay={0.05} />
      <StatBlock label="Claims verified" value={supported} sub={`· of ${claims.length}`} accent="var(--emerald)" delay={0.1} />
      <StatBlock label="Avg. confidence" value={avgConf} accent="var(--emerald)" delay={0.15} />
      <StatBlock label="Time elapsed" value="—" sub="· 12 agents" delay={0.2} />
    </Paper>
  );
}

const verdictCfg: Record<Verdict, { color: string; bg: string; bd: string; glyph: string }> = {
  SUPPORTED: { color: 'var(--emerald)', bg: 'var(--emerald-soft)', bd: '#c3e0ce', glyph: '✓' },
  REFUTED: { color: 'var(--crimson)', bg: 'var(--crimson-soft)', bd: '#f3c7c4', glyph: '✕' },
  UNVERIFIABLE: { color: 'var(--amber)', bg: 'var(--amber-soft)', bd: '#f3dfa8', glyph: '?' },
};

function ConfidenceBar({ pct, color }: { pct: number; color: string }) {
  const [w, setW] = useState(0);
  useEffect(() => {
    const id = setTimeout(() => setW(pct), 200);
    return () => clearTimeout(id);
  }, [pct]);

  return (
    <div style={{ height: 3, background: 'var(--rule-soft)', borderRadius: 2, overflow: 'hidden', flex: 1, minWidth: 60 }}>
      <div style={{ height: '100%', width: `${w * 100}%`, background: color, transition: 'width 1.1s cubic-bezier(.2,.65,.2,1)' }} />
    </div>
  );
}

function ClaimRow({ claim, i }: { claim: Claim; i: number }) {
  const cfg = verdictCfg[claim.verdict];
  return (
    <div
      className="reveal"
      style={{
        animationDelay: `${0.1 + i * 0.07}s`,
        padding: '16px 0',
        borderBottom: '1px solid var(--rule)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
        <div
          style={{
            flexShrink: 0,
            width: 28,
            height: 28,
            borderRadius: '50%',
            background: cfg.bg,
            color: cfg.color,
            border: `1px solid ${cfg.bd}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: 13,
            marginTop: 1,
          }}
        >
          {cfg.glyph}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'baseline', marginBottom: 6 }}>
            <span
              className="mono"
              style={{
                fontSize: 10,
                letterSpacing: '.12em',
                color: cfg.color,
                fontWeight: 600,
                textTransform: 'uppercase',
              }}
            >
              {claim.verdict}
            </span>
            <span className="mono" style={{ fontSize: 10, color: 'var(--muted)' }}>
              confidence {(claim.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <div style={{ fontSize: 14, color: 'var(--ink)', lineHeight: 1.55, marginBottom: 8 }}>{claim.text}</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <ConfidenceBar pct={claim.confidence} color={cfg.color} />
            <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', whiteSpace: 'nowrap' }}>
              {claim.sources.map((s) => s.replace('.pdf', '')).join(' · ')}
            </span>
          </div>
          {claim.evidence && (
            <div
              style={{
                marginTop: 10,
                padding: '8px 12px',
                background: cfg.bg,
                borderLeft: `2px solid ${cfg.color}`,
                borderRadius: '0 3px 3px 0',
                fontSize: 12.5,
                color: 'var(--ink-soft)',
                fontStyle: 'italic',
                lineHeight: 1.5,
              }}
            >
              {claim.evidence}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ReportCard({ report }: { report: string }) {
  return (
    <Paper className="reveal reveal-2" style={{ padding: '28px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Eyebrow>§ report · final</Eyebrow>
        <div style={{ display: 'flex', gap: 6 }}>
          {['Copy', 'Download', 'Share'].map((a) => (
            <button
              key={a}
              className="chip"
              style={{
                fontFamily: 'inherit',
                fontSize: 11,
                fontWeight: 500,
                color: 'var(--ink-soft)',
                background: 'var(--ivory)',
                border: '1px solid var(--rule)',
                borderRadius: 3,
                padding: '5px 11px',
                cursor: 'pointer',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--ink)';
                e.currentTarget.style.color = 'var(--paper)';
                e.currentTarget.style.borderColor = 'var(--ink)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'var(--ivory)';
                e.currentTarget.style.color = 'var(--ink-soft)';
                e.currentTarget.style.borderColor = 'var(--rule)';
              }}
            >
              {a}
            </button>
          ))}
        </div>
      </div>
      <article style={{ maxWidth: 720 }}>
        {report.split('\n').map((line, i) => {
          if (line.startsWith('## '))
            return (
              <h2
                key={i}
                className="serif"
                style={{ fontSize: 34, lineHeight: 1.1, letterSpacing: '-0.02em', marginBottom: 14, color: 'var(--ink)' }}
              >
                {line.slice(3)}
              </h2>
            );
          if (line.startsWith('### '))
            return (
              <h3
                key={i}
                className="serif"
                style={{ fontSize: 20, lineHeight: 1.2, marginTop: 22, marginBottom: 8, color: 'var(--ink)' }}
              >
                <em style={{ color: 'var(--accent)', marginRight: 4 }}>§</em> {line.slice(4)}
              </h3>
            );
          if (line.startsWith('- '))
            return (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: 10,
                  paddingLeft: 0,
                  marginBottom: 6,
                  fontSize: 14.5,
                  color: 'var(--ink-soft)',
                  lineHeight: 1.65,
                }}
              >
                <span style={{ color: 'var(--accent)', fontWeight: 600 }}>→</span>
                <span>{renderWithCitations(line.slice(2))}</span>
              </div>
            );
          if (!line.trim()) return <div key={i} style={{ height: 10 }} />;
          const parts = line.split(/(\*\*[^*]+\*\*)/g);
          return (
            <p key={i} style={{ fontSize: 15, color: 'var(--ink-soft)', lineHeight: 1.75, marginBottom: 10 }}>
              {parts.map((p, j) =>
                p.startsWith('**') && p.endsWith('**') ? (
                  <strong key={j} style={{ color: 'var(--ink)', fontWeight: 600 }}>
                    {p.slice(2, -2)}
                  </strong>
                ) : (
                  <span key={j}>{renderWithCitations(p)}</span>
                )
              )}
            </p>
          );
        })}
      </article>
    </Paper>
  );
}

export function ResultsState({ report, claims, sources }: {
  report: string
  claims: Claim[]
  sources: Source[]
}) {
  const supported = claims.filter((c) => c.verdict === 'SUPPORTED').length;
  const refuted = claims.filter((c) => c.verdict === 'REFUTED').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16, marginBottom: 24 }}>
      <SummaryStrip claims={claims} sources={sources} />
      <div style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 16, alignItems: 'flex-start' }}>
        <ReportCard report={report} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Paper className="reveal reveal-3" style={{ padding: '22px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 4 }}>
              <Eyebrow>§ claims</Eyebrow>
              <span className="mono" style={{ fontSize: 10, color: 'var(--muted)' }}>
                {supported} supported · {refuted} refuted
              </span>
            </div>
            {claims.map((c, i) => (
              <ClaimRow key={i} claim={c} i={i} />
            ))}
          </Paper>

          <Paper className="reveal reveal-4" style={{ padding: '22px 24px' }}>
            <Eyebrow>§ sources</Eyebrow>
            <div style={{ marginTop: 14 }}>
              {sources.map((s, i) => (
                <div
                  key={i}
                  className="reveal"
                  style={{
                    animationDelay: `${0.15 + i * 0.06}s`,
                    display: 'flex',
                    gap: 14,
                    padding: '12px 0',
                    borderBottom: i < sources.length - 1 ? '1px solid var(--rule)' : 'none',
                  }}
                >
                  <span
                    className="serif"
                    style={{
                      fontSize: 20,
                      color: 'var(--accent)',
                      fontStyle: 'italic',
                      minWidth: 22,
                      lineHeight: 1,
                    }}
                  >
                    [{i + 1}]
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500, lineHeight: 1.4 }}>{s.title}</div>
                    <div className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 3, letterSpacing: '.02em' }}>
                      {s.meta}
                    </div>
                  </div>
                  <a href={s.file} target="_blank" rel="noreferrer" className="link-hover" style={{ fontSize: 11, color: 'var(--accent)', flexShrink: 0, alignSelf: 'center' }}>
                    open ↗
                  </a>
                </div>
              ))}
            </div>
          </Paper>
        </div>
      </div>
    </div>
  );
}
