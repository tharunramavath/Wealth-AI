import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { AlertCircle, Info, TrendingUp, TrendingDown, AlertTriangle, RefreshCw } from 'lucide-react';
import { Badge } from './ui/Badge';
import clsx from 'clsx';

const PERIODS = [
  { label: '1M', value: '1M', days: 30 },
  { label: '3M', value: '3M', days: 90 },
  { label: '6M', value: '6M', days: 180 },
  { label: '1Y', value: '1Y', days: 365 },
];

function getCorrelationColor(value) {
  if (value >= 0.7) return { bg: '#dc2626', text: '#dc2626', intensity: 0.2 + (value - 0.7) * 2.67 };
  if (value >= 0.4) return { bg: '#f97316', text: '#f97316', intensity: 0.2 + (value - 0.4) * 0.67 };
  if (value >= 0.2) return { bg: '#fbbf24', text: '#fbbf24', intensity: 0.2 + (value - 0.2) * 2.5 };
  if (value >= -0.2) return { bg: '#f1f5f9', text: '#94a3b8', intensity: 0.5 };
  if (value >= -0.5) return { bg: '#60a5fa', text: '#3b82f6', intensity: 0.2 + (value + 0.5) * -0.67 };
  return { bg: '#1e40af', text: '#1e3a8a', intensity: 0.2 + (value + 1) * 2.67 };
}

export default function CorrelationMatrix() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod] = useState('1Y');
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);

  const fetchCorrelation = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get(`/portfolio/correlation?period=${period}`);
      setData(response.data);
      if (response.data.error) {
        setError(response.data.error);
      }
    } catch {
      setError('Failed to load correlation data');
    }
    setLoading(false);
  }, [period]);

  useEffect(() => {
    fetchCorrelation();
    const handleFocus = () => fetchCorrelation();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [fetchCorrelation]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post('/portfolio/sync-history');
      await fetchCorrelation();
    } catch (err) {
      console.error('Sync failed:', err);
    }
    setSyncing(false);
  };

  if (loading) {
    return (
      <div className="bg-terminal-card border border-terminal-border rounded-xl p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-terminal-border rounded w-1/3"></div>
          <div className="h-64 bg-terminal-border rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-terminal-card border border-terminal-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-terminal-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-text-primary">Correlation Matrix</h3>
          <p className="text-xs text-text-muted mt-0.5">
            {data?.date_range?.start && data?.date_range?.end 
              ? `${data.date_range.start} to ${data.date_range.end} (${data.data_points} data points)`
              : 'Stock correlation analysis'}
          </p>
        </div>
        <div className="flex items-center space-x-1 bg-terminal-surface rounded-lg p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={clsx(
                'px-3 py-1 text-xs font-medium rounded transition-colors',
                period === p.value
                  ? 'bg-accent-cyan text-black'
                  : 'text-text-muted hover:text-text-primary'
              )}
            >
              {p.label}
            </button>
          ))}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="ml-2 px-3 py-1 text-xs font-medium rounded transition-colors bg-bullish/20 text-bullish hover:bg-bullish/30 disabled:opacity-50 flex items-center gap-1"
            title="Sync price history for all stocks"
          >
            <RefreshCw size={12} className={syncing ? 'animate-spin' : ''} />
            Sync
          </button>
        </div>
      </div>

      {error ? (
        <div className="p-6 text-center">
          <AlertCircle className="w-10 h-10 text-text-muted mx-auto mb-3" />
          <p className="text-text-muted text-sm">{error}</p>
          <p className="text-text-muted text-xs mt-2">
            Click "Sync" to load historical data for your stocks.
          </p>
        </div>
      ) : (
        <div className="p-5">
          <div className="flex gap-6">
            <div className="flex-1">
              {data && data.tickers && data.tickers.length >= 2 ? (
                <div className="overflow-auto max-h-[500px]">
                  <table className="w-full border-collapse">
                    <thead className="sticky top-0 z-10 bg-terminal-card">
                      <tr>
                        <th className="p-2 text-xs text-text-muted font-medium bg-terminal-card"></th>
                        {data.tickers.map((ticker) => (
                          <th key={ticker} className="p-2 text-xs text-text-muted font-medium text-center min-w-[50px] bg-terminal-card">
                            {ticker}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {data.tickers.map((rowTicker) => (
                        <tr key={rowTicker}>
                          <td className="p-2 text-xs text-text-muted font-medium text-right pr-3 sticky left-0 bg-terminal-card z-10">
                            {rowTicker}
                          </td>
                          {data.tickers.map((colTicker) => {
                            const value = data.correlation_values?.[rowTicker]?.[colTicker] ?? 0;
                            const color = getCorrelationColor(value);
                            const cellSize = data.tickers.length > 15 ? 'w-9 h-9 text-[10px]' : 'w-12 h-12 text-xs';
                            return (
                              <td key={colTicker} className="p-0.5 text-center">
                                <div
                                  className={`${cellSize} mx-auto rounded flex items-center justify-center font-medium`}
                                  style={{
                                    backgroundColor: rowTicker === colTicker ? '#1e293b' : color.bg,
                                    color: rowTicker === colTicker ? '#64748b' : (value > 0.2 || value < -0.2 ? '#fff' : '#475569'),
                                    opacity: rowTicker === colTicker ? 0.5 : 1,
                                  }}
                                  title={`${rowTicker} vs ${colTicker}: ${value.toFixed(3)}`}
                                >
                                  {value.toFixed(2)}
                                </div>
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="h-48 flex items-center justify-center text-text-muted text-sm">
                  No correlation data available
                </div>
              )}
            </div>

            <div className="w-32 flex-shrink-0">
              <div className="text-xs text-text-muted font-medium mb-3">Legend</div>
              <div className="space-y-2">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#dc2626]"></div>
                    <span className="text-text-secondary">+0.7 to +1.0</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#f97316]"></div>
                    <span className="text-text-secondary">+0.4 to +0.7</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#fbbf24]"></div>
                    <span className="text-text-secondary">+0.2 to +0.4</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#f1f5f9]"></div>
                    <span className="text-text-secondary">-0.2 to +0.2</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#60a5fa]"></div>
                    <span className="text-text-secondary">-0.5 to -0.2</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-5 h-5 rounded bg-[#1e40af]"></div>
                    <span className="text-text-secondary">-1.0 to -0.5</span>
                  </div>
                </div>
                <div className="pt-2 border-t border-terminal-border">
                  <div className="flex items-center gap-2 text-xs">
                    <TrendingUp size={12} className="text-bullish" />
                    <span className="text-text-muted">Move together</span>
                  </div>
                  <div className="flex items-center gap-2 text-xs mt-1">
                    <TrendingUp size={12} className="text-bearish rotate-180" />
                    <span className="text-text-muted">Hedge each other</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {data?.insights && data.insights.length > 0 && (
            <div className="mt-5 pt-4 border-t border-terminal-border space-y-2">
              <div className="text-xs text-text-muted font-medium mb-2">AI Insights</div>
              {data.insights.map((insight, i) => (
                <div
                  key={i}
                  className={clsx(
                    'flex items-start gap-3 p-3 rounded-lg text-sm',
                    insight.type === 'warning' ? 'bg-yellow-500/10 text-yellow-400' :
                    insight.type === 'opportunity' ? 'bg-blue-500/10 text-blue-400' :
                    'bg-green-500/10 text-green-400'
                  )}
                >
                  {insight.type === 'warning' ? (
                    <AlertTriangle size={16} className="flex-shrink-0 mt-0.5" />
                  ) : insight.type === 'opportunity' ? (
                    <Info size={16} className="flex-shrink-0 mt-0.5" />
                  ) : (
                    <TrendingUp size={16} className="flex-shrink-0 mt-0.5" />
                  )}
                  <span className="text-text-primary">{insight.message}</span>
                </div>
              ))}
            </div>
          )}

          {data?.stock_stats && Object.keys(data.stock_stats).length > 0 && (
            <div className="mt-8 pt-6 border-t border-terminal-border">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg">
                    <TrendingUp size={16} className="text-primary" />
                  </div>
                  <div>
                    <h4 className="text-xs font-black text-foreground uppercase tracking-[0.2em]">Asset Performance DNA</h4>
                    <p className="text-[10px] font-bold text-text-muted uppercase tracking-tight italic">Rolling volatility and return analysis</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {data.tickers.map((ticker) => {
                  const stats = data.stock_stats[ticker];
                  const isPositive = stats.mean_return >= 0;
                  return (
                    <div key={ticker} className="group relative bg-accent/20 hover:bg-accent/40 border border-border/50 rounded-2xl p-5 transition-all duration-300 hover:scale-[1.02] hover:shadow-xl hover:shadow-black/5 overflow-hidden">
                      {/* Interactive background glow */}
                      <div className={clsx(
                        "absolute -right-8 -bottom-8 w-24 h-24 blur-3xl opacity-0 group-hover:opacity-20 transition-opacity duration-700 rounded-full",
                        isPositive ? "bg-bullish" : "bg-bearish"
                      )}/>
                      
                      <div className="flex items-center justify-between mb-4 relative z-10">
                        <div className="flex flex-col">
                          <span className="text-sm font-black text-foreground tracking-tight uppercase">{ticker}</span>
                          <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest opacity-60 font-mono">#{data.tickers.indexOf(ticker) + 1}</span>
                        </div>
                        <div className={clsx(
                          "p-2 rounded-xl transition-all duration-500",
                          isPositive ? "bg-bullish/10 text-bullish group-hover:bg-bullish group-hover:text-white" : "bg-bearish/10 text-bearish group-hover:bg-bearish group-hover:text-white"
                        )}>
                          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                        </div>
                      </div>
                      
                      <div className="space-y-3 relative z-10">
                        <StatRow label="Avg Periodic Return" value={`${isPositive ? '+' : ''}${stats.mean_return.toFixed(3)}%`} color={isPositive ? 'text-bullish' : 'text-bearish'} />
                        <StatRow label="Risk Volatility" value={`${stats.volatility.toFixed(2)}%`} />
                        
                        <div className="grid grid-cols-2 gap-2 mt-4 pt-4 border-t border-border/30">
                          <div className="text-center group-hover:translate-y-[-2px] transition-transform">
                             <div className="text-[8px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-1">Up Bias</div>
                             <div className="text-xs font-black text-bullish tabular-nums">{stats.positive_days}d</div>
                          </div>
                          <div className="text-center group-hover:translate-y-[-2px] transition-transform">
                             <div className="text-[8px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-1">Down Bias</div>
                             <div className="text-xs font-black text-bearish tabular-nums">{stats.negative_days}d</div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
 
function StatRow({ label, value, color }) {
  return (
    <div className="flex justify-between items-center text-[10px]">
      <span className="font-bold text-muted-foreground uppercase tracking-tight opacity-70 leading-none">{label}</span>
      <span className={clsx("font-black tabular-nums tracking-tighter leading-none", color || 'text-text-primary')}>{value}</span>
    </div>
  );
}
