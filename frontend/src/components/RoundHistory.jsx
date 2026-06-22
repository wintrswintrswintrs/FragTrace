export default function RoundHistory({ rounds }) {
  return (
    <div
      className="scrollbar-thin"
      style={{
        display: 'flex',
        gap: 3,
        overflowX: 'auto',
        padding: '4px 0',
      }}
    >
      {rounds.map((r) => {
        const winner = (r.winner || '').toLowerCase();
        const isCt = winner === 'ct';
        const isT = winner === 't';
        const color = isCt ? 'var(--ct-blue)' : isT ? 'var(--t-orange)' : 'var(--text-faint)';
        const label = isCt ? 'C' : isT ? 'T' : '-';
        const reasonIcon = roundReasonIcon(r.reason);

        return (
          <div
            key={r.round_num}
            title={`Round ${r.round_num}: ${winner.toUpperCase()} won (${r.reason || 'unknown'})`}
            className="mono"
            style={{
              flex: '0 0 auto',
              width: 26,
              height: 36,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              background: 'var(--panel-raised)',
              border: `1px solid ${color}`,
              borderBottom: `3px solid ${color}`,
              fontSize: 10,
              color: 'var(--text-dim)',
              gap: 2,
            }}
          >
            <span style={{ fontSize: 9, color: 'var(--text-faint)' }}>{r.round_num}</span>
            <span style={{ color, fontWeight: 700, fontSize: 12 }}>
              {reasonIcon || label}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function roundReasonIcon(reason) {
  if (!reason) return null;
  const r = reason.toLowerCase();
  if (r.includes('bomb') && r.includes('defus')) return '◆';
  if (r.includes('bomb') || r.includes('exploded')) return '✸';
  if (r.includes('time')) return '⏱';
  return null;
}
