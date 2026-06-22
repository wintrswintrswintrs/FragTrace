import { useState } from 'react';
import UploadScreen from './components/UploadScreen';
import MatchHeader from './components/MatchHeader';
import Scoreboard from './components/Scoreboard';

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000';

export default function App() {
  const [matchData, setMatchData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleFile(file) {
    setError(null);
    setIsLoading(true);

    const formData = new FormData();
    formData.append('file', file);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 150_000); // 2.5min

    try {
      const res = await fetch(`${API_BASE}/api/parse`, {
        method: 'POST',
        body: formData,
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }

      const data = await res.json();
      setMatchData(data);
    } catch (err) {
      if (err.name === 'AbortError') {
        setError('This is taking longer than expected. Large demos can take a couple minutes — try again, or use a shorter demo.');
      } else {
        setError(err.message || 'Something went wrong while parsing the demo.');
      }
    } finally {
      clearTimeout(timeoutId);
      setIsLoading(false);
    }
  }

  function handleReset() {
    setMatchData(null);
    setError(null);
  }

  if (!matchData) {
    return <UploadScreen onFile={handleFile} error={error} isLoading={isLoading} />;
  }

  return (
    <div style={{ maxWidth: 1100, margin: '0 auto', padding: '32px 20px 80px' }}>
      <MatchHeader data={matchData} onReset={handleReset} />
      <Scoreboard players={matchData.players} />
    </div>
  );
}
