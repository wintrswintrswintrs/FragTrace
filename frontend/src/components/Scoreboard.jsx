const COLUMNS = [
  { key: 'rating', label: 'RTG', width: 56 },
  { key: 'kills', label: 'K', width: 44 },
  { key: 'deaths', label: 'D', width: 44 },
  { key: 'assists', label: 'A', width: 44 },
  { key: 'kd_ratio', label: 'K/D', width: 52 },
  { key: 'adr', label: 'ADR', width: 56 },
  { key: 'kast', label: 'KAST%', width: 64 },
  { key: 'hs_pct', label: 'HS%', width: 56 },
  { key: 'entry_kills', label: 'ENTRY', width: 56 },
  { key: 'clutches_won', label: 'CLUTCH', width: 64 },
  { key: 'utility_damage', label: 'UTIL DMG', width: 76 },
];

export default function Scoreboard({ players }) {
  const teams = groupByTeam(players);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      {teams.map(([teamKey, teamPlayers]) => (
        <TeamTable key={teamKey} teamKey={teamKey} players={teamPlayers} />
      ))}
    </div>
  );
}

function groupByTeam(players) {
  const groups = {};
  for (const p of players) {
    const key = p.team || 'unknown';
    if (!groups[key]) groups[key] = [];
    groups[key].push(p);
  }
  // Stable order: t, ct, then anything else
  const order = ['t', 'ct'];
  const keys = Object.keys(groups).sort((a, b) => {
    const ai = order.indexOf(a);
    const bi = order.indexOf(b);
    if (ai === -1 && bi === -1) return a.localeCompare(b);
    if (ai === -1) return 1;
    if (bi === -1) return -1;
    return ai - bi;
  });
  return keys.map((k) => [k, groups[k]]);
}

function TeamTable({ teamKey, players }) {
  const isCt = teamKey === 'ct';
  const color = isCt ? 'var(--ct-blue)' : teamKey === 't' ? 'var(--t-orange)' : 'var(--text-dim)';
  const label = isCt ? 'CT SIDE' : teamKey === 't' ? 'T SIDE' : 'UNASSIGNED';

  return (
    <div className="hud-panel" style={{ overflow: 'hidden' }}>
      <div
        className="mono"
        style={{
          padding: '10px 16px',
          background: 'var(--panel-raised)',
          borderBottom: `2px solid ${color}`,
          color,
          fontSize: 12,
          letterSpacing: '0.15em',
          fontWeight: 700,
        }}
      >
        {label}
      </div>

      <div style={{ overflowX: 'auto' }} className="scrollbar-thin">
        <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 760 }}>
          <thead>
            <tr>
              <th style={headerCellStyle('left', 180)}>PLAYER</th>
              {COLUMNS.map((c) => (
                <th key={c.key} style={headerCellStyle('right', c.width)}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {players
              .slice()
              .sort((a, b) => b.rating - a.rating)
              .map((p, idx) => (
                <tr
                  key={p.steamid}
                  style={{
                    borderTop: '1px solid var(--line)',
                    background: idx % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.015)',
                  }}
                >
                  <td style={{ ...bodyCellStyle('left'), display: 'flex', alignItems: 'center', gap: 8 }}>
                    <MultiKillBadge multiKills={p.multi_kills} />
                    <span style={{ fontWeight: 600 }}>{p.name}</span>
                  </td>
                  <td className="mono" style={{ ...bodyCellStyle('right'), color: ratingColor(p.rating), fontWeight: 700 }}>
                    {p.rating.toFixed(2)}
                  </td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.kills}</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.deaths}</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.assists}</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.kd_ratio.toFixed(2)}</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.adr.toFixed(1)}</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.kast.toFixed(1)}%</td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.hs_pct.toFixed(1)}%</td>
                  <td className="mono" style={bodyCellStyle('right')}>
                    {p.entry_kills}/{p.entry_attempts}
                  </td>
                  <td className="mono" style={bodyCellStyle('right')}>
                    {p.clutches_won > 0 ? (
                      <span style={{ color: 'var(--gold)' }}>
                        {p.clutches_won}/{p.clutches_played}
                      </span>
                    ) : (
                      `${p.clutches_won}/${p.clutches_played}`
                    )}
                  </td>
                  <td className="mono" style={bodyCellStyle('right')}>{p.utility_damage}</td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MultiKillBadge({ multiKills }) {
  if (!multiKills) return null;
  if (multiKills['5k'] > 0) return <Badge text="ACE" color="var(--gold)" />;
  if (multiKills['4k'] > 0) return <Badge text="4K" color="var(--t-orange)" />;
  if (multiKills['3k'] > 0) return <Badge text="3K" color="var(--ct-blue)" />;
  return <span style={{ width: 28, display: 'inline-block' }} />;
}

function Badge({ text, color }) {
  return (
    <span
      className="mono"
      style={{
        fontSize: 9,
        fontWeight: 800,
        color: '#0a0d0b',
        background: color,
        padding: '2px 5px',
        letterSpacing: '0.05em',
      }}
    >
      {text}
    </span>
  );
}

function ratingColor(rating) {
  if (rating >= 1.3) return 'var(--green)';
  if (rating >= 1.0) return 'var(--text)';
  return 'var(--red)';
}

function headerCellStyle(align, width) {
  return {
    textAlign: align,
    padding: '10px 12px',
    fontSize: 11,
    color: 'var(--text-faint)',
    letterSpacing: '0.08em',
    fontWeight: 600,
    width,
    whiteSpace: 'nowrap',
  };
}

function bodyCellStyle(align) {
  return {
    textAlign: align,
    padding: '10px 12px',
    fontSize: 13,
    whiteSpace: 'nowrap',
  };
}
