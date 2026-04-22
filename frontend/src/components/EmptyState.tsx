import { Paper, Eyebrow } from './Primitives';
import { useTyping } from '../hooks/useTyping';

export function EmptyState() {
  const query = useTyping('What are the main differences between A2A and MCP?', 32, 500);
  const done = query.length >= 58;

  return (
    <Paper
      className="reveal reveal-3"
      style={{ padding: '48px 40px', marginBottom: 20, position: 'relative', overflow: 'hidden' }}
    >
      {/* Decorative grid watermark */}
      <svg
        style={{ position: 'absolute', top: -40, right: -40, opacity: 0.35, pointerEvents: 'none' }}
        width="280"
        height="280"
        viewBox="0 0 280 280"
      >
        <defs>
          <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
            <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--rule)" strokeWidth="0.8" />
          </pattern>
        </defs>
        <rect width="280" height="280" fill="url(#grid)" />
        <circle cx="140" cy="140" r="90" fill="none" stroke="var(--accent)" strokeWidth="0.5" opacity=".3" strokeDasharray="2 4" />
        <circle cx="140" cy="140" r="60" fill="none" stroke="var(--accent)" strokeWidth="0.5" opacity=".5" />
        <circle cx="140" cy="140" r="30" fill="var(--accent-soft)" opacity=".6" />
      </svg>

      <div style={{ position: 'relative', zIndex: 1, maxWidth: 680 }}>
        <Eyebrow dot>Ready</Eyebrow>
        <h2
          className="serif"
          style={{ fontSize: 44, lineHeight: 1.05, marginTop: 16, letterSpacing: '-0.02em' }}
        >
          Start by asking a<br />
          <em style={{ color: 'var(--accent)' }}>research question</em>.
        </h2>
        <p style={{ fontSize: 15, color: 'var(--ink-soft)', marginTop: 14, lineHeight: 1.6, maxWidth: 540 }}>
          Twelve specialist agents will retrieve passages from the local corpus, cross-verify every claim, and return a report with inline citations.
        </p>

        {/* Sample query with typing effect */}
        <div
          style={{
            marginTop: 28,
            padding: '14px 18px',
            background: 'var(--ivory-2)',
            border: '1px dashed var(--rule)',
            borderRadius: 3,
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            maxWidth: 580,
          }}
        >
          <span className="mono" style={{ color: 'var(--accent)', fontSize: 13, fontWeight: 600 }}>
            ❯
          </span>
          <span className={done ? '' : 'caret'} style={{ fontSize: 13.5, color: 'var(--ink)', fontFamily: 'Inter, sans-serif' }}>
            {query}
          </span>
        </div>

        <div style={{ display: 'flex', gap: 24, marginTop: 32, flexWrap: 'wrap' }}>
          <div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 4 }}>
              Agents
            </div>
            <div className="serif" style={{ fontSize: 28, color: 'var(--ink)' }}>12</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 4 }}>
              Stages
            </div>
            <div className="serif" style={{ fontSize: 28, color: 'var(--ink)' }}>5</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 4 }}>
              Docs indexed
            </div>
            <div className="serif" style={{ fontSize: 28, color: 'var(--ink)' }}>1,284</div>
          </div>
          <div>
            <div className="mono" style={{ fontSize: 10, color: 'var(--muted)', letterSpacing: '.15em', textTransform: 'uppercase', marginBottom: 4 }}>
              Avg. latency
            </div>
            <div className="serif" style={{ fontSize: 28, color: 'var(--ink)' }}>~42s</div>
          </div>
        </div>
      </div>
    </Paper>
  );
}
