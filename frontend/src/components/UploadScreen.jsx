import { useCallback, useRef, useState } from 'react';

export default function UploadScreen({ onFile, error, isLoading }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      const file = e.dataTransfer.files?.[0];
      if (file) onFile(file);
    },
    [onFile]
  );

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
      }}
    >
      <div style={{ textAlign: 'center', marginBottom: 48 }}>
        <div
          className="mono"
          style={{
            color: 'var(--text-faint)',
            fontSize: 13,
            letterSpacing: '0.2em',
            marginBottom: 16,
          }}
        >
          GOTV // DEMO ANALYSIS
        </div>
        <h1
          className="mono"
          style={{
            fontSize: 'clamp(36px, 6vw, 64px)',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}
        >
          <span style={{ color: 'var(--t-orange)' }}>FRAG</span>
          <span style={{ color: 'var(--text)' }}>TRACE</span>
        </h1>
        <p style={{ color: 'var(--text-dim)', marginTop: 16, fontSize: 16, maxWidth: 480 }}>
          Drop a CS2 demo file. We'll parse every round, kill, and clutch and
          hand you back the full scoreboard.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className="hud-panel"
        style={{
          width: 'min(560px, 90vw)',
          padding: '56px 32px',
          textAlign: 'center',
          cursor: 'pointer',
          borderColor: isDragging ? 'var(--t-orange)' : 'var(--line)',
          background: isDragging ? 'var(--panel-raised)' : 'var(--panel)',
          transition: 'border-color 120ms, background 120ms',
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".dem"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFile(file);
          }}
        />

        {isLoading ? (
          <>
            <div
              className="mono"
              style={{ color: 'var(--t-orange)', fontSize: 14, letterSpacing: '0.15em' }}
            >
              PARSING DEMO...
            </div>
            <div style={{ color: 'var(--text-faint)', fontSize: 13, marginTop: 8 }}>
              Larger demos can take a minute or two.
            </div>
            <ProgressBar />
          </>
        ) : (
          <>
            <div
              className="mono"
              style={{ fontSize: 13, color: 'var(--text-dim)', letterSpacing: '0.1em' }}
            >
              DRAG .DEM FILE HERE
            </div>
            <div style={{ color: 'var(--text-faint)', fontSize: 13, marginTop: 8 }}>
              or click to browse
            </div>
          </>
        )}
      </div>

      {error && (
        <div
          className="mono"
          style={{
            marginTop: 20,
            color: 'var(--red)',
            fontSize: 13,
            maxWidth: 480,
            textAlign: 'center',
          }}
        >
          {error}
        </div>
      )}

      <div style={{ marginTop: 56, color: 'var(--text-faint)', fontSize: 12, maxWidth: 520, textAlign: 'center', lineHeight: 1.6 }}>
        Your demo is parsed on the server and never leaves this analysis —
        we read kills, damage, and round events directly from the replay file.
        Works best with demos under ~80MB; very long matches or overtime
        games may be too large for the free hosting tier this runs on.
      </div>
    </div>
  );
}

function ProgressBar() {
  return (
    <div
      style={{
        marginTop: 20,
        width: 200,
        height: 3,
        background: 'var(--line)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      <div
        style={{
          position: 'absolute',
          height: '100%',
          width: '40%',
          background: 'var(--t-orange)',
          animation: 'slide 1.1s ease-in-out infinite',
        }}
      />
      <style>{`
        @keyframes slide {
          0% { left: -40%; }
          100% { left: 100%; }
        }
      `}</style>
    </div>
  );
}
