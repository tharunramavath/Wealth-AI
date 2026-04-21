import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { Radio } from 'lucide-react';

export default function NBAHistory() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/nba/history')
      .then(r => setHistory(r.data))
      .catch(() => setHistory([]))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="animate-pulse h-32 bg-terminal-card rounded-xl" />;

  if (!history.length) return <div className="bg-terminal-card border border-terminal-border rounded-xl p-8 text-center text-text-muted">No NBA history found.</div>;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-text-primary mb-4">NBA Action History</h1>
      <div className="space-y-4">
        {history.map((rec, i) => (
          <div key={rec.rec_id || i} className="bg-terminal-card border border-terminal-border rounded-xl p-5">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs text-text-muted">{new Date(rec.created_at).toLocaleString()}</span>
              <span className="text-xs font-medium text-bullish">Confidence: {Math.round((rec.confidence_score || 0) * 100)}%</span>
            </div>
            
            {rec.triggering_event && (
              <div className="mb-3 p-3 bg-terminal-bg rounded-lg border-l-2 border-accent-purple">
                <div className="flex items-center gap-2 mb-1">
                  <Radio size={12} className="text-accent-purple" />
                  <span className="text-xs font-medium text-accent-purple">Event-Triggered</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    rec.triggering_event.severity === 'Critical' ? 'bg-bearish/20 text-bearish' :
                    rec.triggering_event.severity === 'High' ? 'bg-accent-gold/20 text-accent-gold' :
                    'bg-accent-cyan/20 text-accent-cyan'
                  }`}>
                    {rec.triggering_event.severity}
                  </span>
                  <span className="text-xs text-text-muted">{rec.triggering_event.sector}</span>
                </div>
                <p className="text-sm text-text-secondary">{rec.triggering_event.headline}</p>
              </div>
            )}
            
            <div className="mb-2">
              <span className="font-semibold text-text-primary">Market Insight:</span>
              <span className="ml-2 text-text-secondary">{rec.market_insight || 'N/A'}</span>
            </div>
            <div className="mb-2">
              <span className="font-semibold text-text-primary">Action:</span>
              <span className="ml-2 text-text-secondary">{rec.next_best_action || 'N/A'}</span>
            </div>
            <div className="mb-2">
              <span className="font-semibold text-text-primary">Portfolio Impact:</span>
              <span className="ml-2 text-text-secondary">{rec.portfolio_impact || 'N/A'}</span>
            </div>
            {rec.flags && rec.flags.length > 0 && (
              <div className="mt-2 text-xs text-bearish">Flags: {rec.flags.join(', ')}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
