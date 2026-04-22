import type { UIState } from '../types';

const NAV_STATES: UIState[] = ['empty', 'loading', 'results'];
const NAV_LABELS: Record<UIState, string> = {
  empty: 'Idle',
  loading: 'Running',
  results: 'Complete',
};

interface StateNavProps {
  current: UIState;
  onChange: (s: UIState) => void;
}

export function StateNav({ current, onChange }: StateNavProps) {
  return (
    <div
      style={{
        display: 'inline-flex',
        padding: 3,
        background: 'var(--paper)',
        border: '1px solid var(--rule)',
        borderRadius: 4,
        marginBottom: 24,
      }}
    >
      {NAV_STATES.map((s, i) => {
        const on = current === s;
        return (
          <button
            key={s}
            onClick={() => onChange(s)}
            style={{
              fontFamily: 'inherit',
              fontSize: 11.5,
              fontWeight: on ? 600 : 500,
              letterSpacing: '.05em',
              textTransform: 'uppercase',
              color: on ? 'var(--paper)' : 'var(--ink-soft)',
              background: on ? 'var(--ink)' : 'transparent',
              border: 'none',
              borderRadius: 3,
              padding: '7px 16px',
              cursor: 'pointer',
              transition: 'all .2s',
            }}
          >
            <span style={{ fontSize: 9, color: on ? 'var(--muted-2)' : 'var(--muted)', marginRight: 8 }}>
              0{i + 1}
            </span>
            {NAV_LABELS[s]}
          </button>
        );
      })}
    </div>
  );
}
