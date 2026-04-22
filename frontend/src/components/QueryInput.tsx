import { useState } from 'react';
import { Paper, Eyebrow } from './Primitives';
import { EXAMPLES } from '../mocks/data';
import type { UIState } from '../types';

interface QueryInputProps {
  onSubmit: () => void;
  state: UIState;
}

export function QueryInput({ onSubmit, state }: QueryInputProps) {
  const [val, setVal] = useState('');
  const [focus, setFocus] = useState(false);
  const disabled = state === 'loading';

  const onKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      if (!disabled && val.trim()) onSubmit();
    }
  };

  return (
    <Paper className="reveal" style={{ padding: 0, overflow: 'hidden' }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          padding: '10px 16px',
          borderBottom: '1px solid var(--rule)',
          background: 'var(--ivory)',
        }}
      >
        <div style={{ display: 'flex', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#d9d3c1' }} />
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#d9d3c1' }} />
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent)' }} />
        </div>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', letterSpacing: '.12em' }}>
          a2a.research › query
        </span>
        <div style={{ flex: 1 }} />
        <span className="mono" style={{ fontSize: 10, color: 'var(--muted-2)' }}>
          {val.length}/2000
        </span>
      </div>

      <div style={{ padding: '22px 24px 18px' }}>
        <Eyebrow>§ 01 · Research Query</Eyebrow>
        <div style={{ marginTop: 14, position: 'relative' }}>
          <div
            style={{
              position: 'absolute',
              left: 0,
              top: 14,
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: 14,
              color: val ? 'var(--accent)' : 'var(--muted-2)',
              fontWeight: 600,
              pointerEvents: 'none',
            }}
          >
            ❯
          </div>
          <textarea
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={onKey}
            onFocus={() => setFocus(true)}
            onBlur={() => setFocus(false)}
            placeholder="Ask a research question…"
            rows={3}
            disabled={disabled}
            style={{
              width: '100%',
              resize: 'vertical',
              fontFamily: 'inherit',
              fontSize: 15,
              lineHeight: 1.6,
              color: 'var(--ink)',
              border: 'none',
              outline: 'none',
              background: 'transparent',
              paddingLeft: 22,
              paddingRight: 4,
              paddingTop: 10,
              paddingBottom: 10,
              borderBottom: `1px solid ${focus ? 'var(--accent)' : 'var(--rule)'}`,
              transition: 'border-color .2s',
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16, flexWrap: 'wrap', gap: 10 }}>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {EXAMPLES.map((ex, i) => (
              <button
                key={i}
                className="chip"
                onClick={() => setVal(ex)}
                style={{
                  fontSize: 11.5,
                  fontFamily: 'inherit',
                  fontWeight: 500,
                  color: 'var(--ink-soft)',
                  background: 'var(--ivory)',
                  border: '1px solid var(--rule)',
                  borderRadius: 3,
                  padding: '5px 11px',
                  cursor: 'pointer',
                  maxWidth: 240,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'var(--accent-soft)';
                  e.currentTarget.style.color = 'var(--accent)';
                  e.currentTarget.style.borderColor = '#c8d1ff';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'var(--ivory)';
                  e.currentTarget.style.color = 'var(--ink-soft)';
                  e.currentTarget.style.borderColor = 'var(--rule)';
                }}
                title={ex}
              >
                ↳ {ex.slice(0, 42)}{ex.length > 42 ? '…' : ''}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
            <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
              <kbd>⌘</kbd> <kbd>↵</kbd>
            </span>
            <button
              className="btn-primary"
              onClick={() => {
                if (!disabled && val.trim()) onSubmit();
              }}
              disabled={disabled || !val.trim()}
              style={{
                fontFamily: 'inherit',
                fontSize: 12.5,
                fontWeight: 600,
                letterSpacing: '.04em',
                color: disabled ? 'var(--muted)' : '#fff',
                background: disabled ? 'var(--ivory-2)' : !val.trim() ? 'var(--muted-2)' : 'var(--ink)',
                border: 'none',
                borderRadius: 3,
                padding: '10px 22px',
                cursor: disabled || !val.trim() ? 'not-allowed' : 'pointer',
                textTransform: 'uppercase',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
              }}
            >
              {disabled ? (
                <>
                  <span
                    style={{
                      width: 10,
                      height: 10,
                      border: '1.5px solid var(--muted)',
                      borderTopColor: 'transparent',
                      borderRadius: '50%',
                      animation: 'spin 0.8s linear infinite',
                      display: 'inline-block',
                    }}
                  />
                  Running
                </>
              ) : (
                <>Run pipeline →</>
              )}
            </button>
          </div>
        </div>
      </div>
    </Paper>
  );
}
