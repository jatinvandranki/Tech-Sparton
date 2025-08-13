import React, { useState } from 'react';
import './App.css';

const formatNumber = (num) => {
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)}B`;
  if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
  if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
  return num;
};

const ModelCard = ({ title, data }) => {
  const isCracked = data.cracked;
  const statusIcon = data.cracked === null ? '⏳' : (isCracked ? '✅' : '❌');
  
  return (
    <div className="model-card">
      <h2>
        {title}
        <span className="status-icon" title={isCracked ? "Success" : "Failed"}>{statusIcon}</span>
      </h2>
      <div className="metrics">
        <div className="metric-item">
          <span>Efficiency (Guesses)</span>
          <strong>{formatNumber(data.wordlist_size)}</strong>
        </div>
        <div className="metric-item">
          <span>Time Consumption</span>
          <strong>{typeof data.time === 'number' ? `${data.time} ms` : data.time}</strong>
        </div>
        <div className="metric-item">
          <span>Computational Power</span>
          <strong>{title.includes('Brute') ? 'Extreme' : (title.includes('Dictionary') ? 'Low' : 'High')}</strong>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [url, setUrl] = useState('');
  const [targetHash, setTargetHash] = useState('');
  const [result, setResult] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setResult(null);
    try {
      const response = await fetch('http://127.0.0.1:5000/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, target_hash: targetHash }),
      });
      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ error: "Failed to connect to the backend. Is it running?" });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container">
      <div className="card">
        <h1>Nexus</h1>
        <p className="subtitle">Attack Vector Analysis Framework</p>
        
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <input type="text" className="input-field" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Target URL for OSINT" required />
            <input type="text" className="input-field" value={targetHash} onChange={(e) => setTargetHash(e.target.value)} placeholder="MD5 Hash to Crack" required />
          </div>
          <button type="submit" disabled={isLoading}>
            {isLoading ? 'Executing Analysis...' : 'Launch Comparative Analysis'}
          </button>
        </form>

        {result && (
          <div className="results-container">
            {result.error ? (
              <p className="error-message">{result.error}</p>
            ) : (
              <div className="comparison-grid">
                <ModelCard title="Dictionary Attack" data={result.results.dictionary} />
                <ModelCard title="Brute-Force Attack" data={result.results.brute_force} />
                <ModelCard title="AI (LSTM) Attack" data={result.results.ai_only} />
                <ModelCard title="Hybrid (AI + Rules)" data={result.results.hybrid} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;