import RoundHistory from './RoundHistory';

export default function MatchHeader({ data, onReset }) {
  const { map, final_score, total_rounds, rounds } = data;
  const tWon = final_score.t > final_score.ct;
  const ctWon = final_score.ct > final_score.t;

  return (
    <div className="hud-panel" style={{ padding: '20px 24px', marginBottom: 24 }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'flex-start',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div className="mono" style={{ fontSize: 11, color: 'var(--text-faint)', letterSpacing: '0.15em' }}>
            {map?.toUpperCase()} · {total_rounds} ROUNDS
          </div>
          <div
            className="mono"
            style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 4 }}
          >
            <span style={{ fontSize: 36, fontWeight: 800, color: tWon ? 'var(--t-orange)' : 'var(--text-dim)' }}>
              {final_score.t}
            </span>
            <span style={{ fontSize: 18, color: 'var(--text-faint)' }}>:</span>
            <span style={{ fontSize: 36, fontWeight: 800, color: ctWon ? 'var(--ct-blue)' : 'var(--text-dim)' }}>
              {final_score.ct}
            </span>
            <span style={{ fontSize: 12, color: 'var(--text-faint)', marginLeft: 8 }}>
              T&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;CT
            </span>
          </div>
        </div>

        <button
          onClick={onReset}
          className="mono"
          style={{
            background: 'transparent',
            border: '1px solid var(--line)',
            color: 'var(--text-dim)',
            fontSize: 11,
            letterSpacing: '0.1em',
            padding: '8px 14px',
          }}
        >
          ↺ NEW DEMO
        </button>
      </div>

      {rounds?.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <RoundHistory rounds={rounds} />
        </div>
      )}
    </div>
  );
}
