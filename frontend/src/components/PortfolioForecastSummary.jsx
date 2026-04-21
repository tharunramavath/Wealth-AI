import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { ArrowUp, ArrowDown, Info, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import clsx from 'clsx';
import { cn } from '../lib/utils';
import ForecastChart from './ForecastChart';

export default function PortfolioForecastSummary() {
  const [forecasts, setForecasts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTicker, setSelectedTicker] = useState(null);
  const [showDetailed, setShowDetailed] = useState(false);
  const [syncing, setSyncing] = useState(false);

  const fetchPortfolioForecasts = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get('/forecast/portfolio/price-summary?days=30');
      if (response.data && response.data.forecasts) {
        setForecasts(response.data.forecasts);
      }
    } catch (err) {
      console.error('Failed to fetch forecasts:', err);
      try {
        const portfolioRes = await api.get('/portfolio');
        if (portfolioRes.data && portfolioRes.data.holdings) {
          const allForecasts = [];
          for (const holding of portfolioRes.data.holdings) {
            if (holding.ticker === 'Cash') continue;
            try {
              const forecastRes = await api.get(`/forecast/${encodeURIComponent(holding.ticker)}?days=30`);
              if (forecastRes.data && forecastRes.data.price_forecast && !forecastRes.data.price_forecast.error) {
                const pf = forecastRes.data.price_forecast;
                allForecasts.push({
                  ticker: holding.ticker,
                  current_price: pf.last_price,
                  predicted_price: pf.predicted_price,
                  expected_change_pct: pf.expected_change_pct,
                  trend_direction: pf.trend_direction,
                  upper_bound: pf.upper_bound?.[pf.upper_bound.length - 1] || 0,
                  lower_bound: pf.lower_bound?.[pf.lower_bound.length - 1] || 0,
                });
              }
            } catch (e) {
              console.error(`Failed to fetch forecast for ${holding.ticker}:`, e);
            }
          }
          setForecasts(allForecasts);
        }
      } catch (e) {
        console.error('Failed to fetch portfolio:', e);
      }
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchPortfolioForecasts();
    const handleFocus = () => fetchPortfolioForecasts();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, [fetchPortfolioForecasts]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await api.post('/portfolio/sync-history');
      await fetchPortfolioForecasts();
    } catch (err) {
      console.error('Sync failed:', err);
    }
    setSyncing(false);
  };

  if (loading) {
    return (
      <div className="bg-terminal-card border border-terminal-border rounded-xl p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-terminal-border rounded w-1/3"></div>
          <div className="h-24 bg-terminal-border rounded"></div>
        </div>
      </div>
    );
  }

  if (!forecasts || forecasts.length === 0) {
    return (
      <div className="bg-terminal-card border border-terminal-border rounded-xl p-6">
        <div className="text-center py-6">
          <p className="text-text-muted text-sm">Portfolio forecast unavailable</p>
          <p className="text-text-muted text-xs mt-1">Click "Sync" to load historical data for your stocks</p>
          <button
            onClick={handleSync}
            disabled={syncing}
            className="mt-3 px-4 py-2 text-xs font-medium rounded-lg transition-colors bg-bullish text-primary-foreground hover:bg-bullish/90 disabled:opacity-50 flex items-center gap-2 mx-auto"
          >
            <RefreshCw size={14} className={syncing ? 'animate-spin' : ''} />
            Sync Data
          </button>
        </div>
      </div>
    );
  }

  if (showDetailed && selectedTicker) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <button
            onClick={() => {
              setShowDetailed(false);
              setSelectedTicker(null);
            }}
            className="text-sm text-accent-cyan hover:underline"
          >
            Back to summary
          </button>
        </div>
        <ForecastChart key={`forecast-${selectedTicker}`} ticker={selectedTicker} />
      </div>
    );
  }

  const bullishCount = forecasts.filter(f => f.trend_direction === 'UPWARD').length;
  const bearishCount = forecasts.filter(f => f.trend_direction === 'DOWNWARD').length;

  return (
    <div className="bg-terminal-card border border-terminal-border rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-terminal-border flex items-center justify-between">
        <div>
          <h3 className="font-semibold text-text-primary">Portfolio Forecasts</h3>
          <p className="text-xs text-text-muted mt-0.5">
            AI-powered price predictions - click for details
          </p>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-3 py-1 text-xs font-medium rounded transition-colors bg-bullish/20 text-bullish hover:bg-bullish/30 disabled:opacity-50 flex items-center gap-1"
            title="Sync price history for all stocks"
          >
            <RefreshCw size={12} className={syncing ? 'animate-spin' : ''} />
            Sync
          </button>
          <span className="flex items-center gap-1 text-bullish">
            <ArrowUp size={12} /> {bullishCount} Bullish
          </span>
          <span className="flex items-center gap-1 text-bearish">
            <ArrowDown size={12} /> {bearishCount} Bearish
          </span>
        </div>
      </div>

      <div className="p-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {forecasts.map((forecast) => {
            const isUpward = forecast.trend_direction === 'UPWARD';
            const isDownward = forecast.trend_direction === 'DOWNWARD';
            const expectedPct = forecast.expected_change_pct || 0;
            
            return (
              <div
                key={forecast.ticker}
                onClick={() => {
                  setSelectedTicker(forecast.ticker);
                  setShowDetailed(true);
                }}
                className={clsx(
                  'group relative bg-accent/20 p-5 rounded-[2rem] cursor-pointer transition-all duration-500 border border-border/50 hover:scale-[1.03] hover:bg-accent/40',
                  isUpward ? 'hover:border-bullish/50 hover:shadow-2xl hover:shadow-bullish/10' :
                  isDownward ? 'hover:border-bearish/50 hover:shadow-2xl hover:shadow-bearish/10' :
                  'hover:border-primary/50'
                )}
              >
                {/* Visual indicator glow */}
                <div className={clsx(
                  "absolute -right-4 -top-4 w-16 h-16 blur-2xl opacity-0 group-hover:opacity-10 transition-opacity duration-700 rounded-full",
                  isUpward ? "bg-bullish" : "bg-bearish"
                )}/>

                <div className="flex items-center justify-between mb-5 relative z-10">
                  <div className="flex flex-col">
                    <span className="text-xl font-black text-foreground tracking-tighter uppercase leading-none">{forecast.ticker}</span>
                    <span className="text-[8px] font-black text-muted-foreground uppercase tracking-[0.2em] mt-1 opacity-60">Intelligence Target</span>
                  </div>
                  <div className={clsx(
                    "w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-500 shadow-sm border border-transparent group-hover:border-white/10",
                    isUpward ? 'bg-bullish/10 text-bullish group-hover:bg-bullish group-hover:text-white' :
                    isDownward ? 'bg-bearish/10 text-bearish group-hover:bg-bearish group-hover:text-white' :
                    'bg-muted text-muted-foreground'
                  )}>
                    {isUpward && <TrendingUp size={18} className={clsx(isUpward && "animate-pulse")} />}
                    {isDownward && <TrendingDown size={18} className={clsx(isDownward && "animate-pulse")} />}
                  </div>
                </div>
                
                <div className="space-y-3 relative z-10">
                  <ForecastMetric label="Current Spot" value={`₹${(forecast.current_price || 0).toLocaleString()}`} />
                  <ForecastMetric 
                    label="Projected Exit" 
                    value={`₹${(forecast.predicted_price || 0).toLocaleString()}`} 
                    color={isUpward ? 'text-bullish' : isDownward ? 'text-bearish' : ''}
                    primary
                  />
                  <ForecastMetric 
                    label="Yield Variance" 
                    value={`${expectedPct >= 0 ? '+' : ''}${expectedPct.toFixed(2)}%`}
                    badge={isUpward ? 'bullish' : isDownward ? 'bearish' : 'secondary'}
                  />
                </div>

                <div className="mt-5 pt-4 border-t border-border/30 relative z-10">
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-[8px] font-black text-muted-foreground uppercase tracking-[0.2em] opacity-60">Probabilistic Range</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-black text-bearish tabular-nums tracking-tighter">₹{((forecast.lower_bound) || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
                    <div className="flex-1 flex items-center justify-center opacity-40 group-hover:opacity-100 transition-all duration-700">
                      {isUpward && (
                        <svg width="40" height="12" viewBox="0 0 40 12" className="text-bullish">
                          <path d="M0 10 L8 10 L8 7 L16 7 L16 4 L24 4 L24 2 L32 2 L32 0 L40 0" 
                            fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                      {isDownward && (
                        <svg width="40" height="12" viewBox="0 0 40 12" className="text-bearish">
                          <path d="M0 2 L8 2 L8 5 L16 5 L16 8 L24 8 L24 10 L32 10 L32 12 L40 12" 
                            fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      )}
                      {!isUpward && !isDownward && (
                        <div className="h-0.5 w-full bg-border rounded-full" />
                      )}
                    </div>
                    <span className="text-[10px] font-black text-bullish tabular-nums tracking-tighter">₹{((forecast.upper_bound) || 0).toLocaleString(undefined, {maximumFractionDigits: 0})}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-4 p-3 bg-terminal-surface rounded-lg flex items-start gap-2">
          <Info size={14} className="text-accent-cyan flex-shrink-0 mt-0.5" />
          <p className="text-xs text-text-secondary">
            Click on any stock to view detailed Prophet forecast with GARCH volatility analysis.
            Predictions are based on historical patterns and may not reflect future performance.
          </p>
        </div>
      </div>
    </div>
  );
}
 
function ForecastMetric({ label, value, color, primary, badge }) {
  return (
    <div className="flex justify-between items-center text-[10px]">
      <span className="font-bold text-muted-foreground uppercase tracking-tight opacity-70 leading-none">{label}</span>
      {badge ? (
        <span className={clsx(
          "px-2 py-0.5 rounded-full font-black tabular-nums scale-90",
          badge === 'bullish' ? 'bg-bullish/10 text-bullish' : 
          badge === 'bearish' ? 'bg-bearish/10 text-bearish' : 
          'bg-accent text-foreground'
        )}>
          {value}
        </span>
      ) : (
        <span className={clsx(
          "font-black tabular-nums tracking-tighter leading-none", 
          primary ? "text-sm text-foreground" : "text-muted-foreground",
          color || ''
        )}>
          {value}
        </span>
      )}
    </div>
  );
}
