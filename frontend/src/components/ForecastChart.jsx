import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { TrendingUp, TrendingDown, AlertTriangle, Info, ArrowUp, ArrowDown, Minus } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts';
import clsx from 'clsx';

const FORECAST_DAYS = [
  { label: '45D', value: 45 },
  { label: '90D', value: 90 },
  { label: '180D', value: 180 },
  { label: '1Y', value: 360 },
  { label: '3Y', value: 1095 },
  { label: '5Y', value: 1825 },
];

function formatINR(value) {
  if (!value && value !== 0) return '₹0';
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return `₹${value.toLocaleString()}`;
}

export default function ForecastChart({ ticker, compact = false }) {
  const [days, setDays] = useState(90);
  const [forecast, setForecast] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setForecast(null);

    api.get(`/forecast/${encodeURIComponent(ticker)}?days=${days}`)
      .then(res => {
        setForecast(res.data);
        if (res.data.error) setError(res.data.error);
      })
      .catch(err => {
        console.error('Forecast error:', err);
        setError('Failed to load forecast');
      })
      .finally(() => setLoading(false));
  }, [ticker, days]);

  const priceForecast = forecast?.price_forecast;
  const isUpward = priceForecast?.trend_direction === 'UPWARD';
  const changeColor = isUpward ? 'text-bullish' : 'text-bearish';
  const TrendIcon = isUpward ? TrendingUp : TrendingDown;

  const chartData = priceForecast ? [
    ...(priceForecast.historical_prices || []).map((price, i) => ({
      date: priceForecast.historical_dates?.[i] || `D${i}`,
      price,
      upper: null,
      lower: null,
    })),
    ...(priceForecast.trend_line || []).map((price, i) => ({
      date: priceForecast.dates?.[i] || `F${i}`,
      price,
      upper: priceForecast.upper_bound?.[i],
      lower: priceForecast.lower_bound?.[i],
    })),
  ].filter(d => d.price != null) : [];

  const lastUpper = priceForecast?.upper_bound?.[priceForecast.upper_bound.length - 1];
  const lastLower = priceForecast?.lower_bound?.[priceForecast.lower_bound.length - 1];

  if (compact) {
    return (
      <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-sm text-text-muted font-medium">{ticker}</span>
            <span className={clsx("text-sm font-semibold flex items-center gap-1", changeColor)}>
              {isUpward ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
              {priceForecast?.expected_change_pct >= 0 ? '+' : ''}{priceForecast?.expected_change_pct?.toFixed(1) || 0}%
            </span>
          </div>
          <div className="flex items-center justify-between text-xs text-text-muted">
            <span>Target: {formatINR(priceForecast?.predicted_price)}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-terminal-card border border-terminal-border rounded-xl overflow-hidden p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="font-semibold text-text-primary flex items-center gap-2">
            {isUpward ? <TrendingUp className="text-bullish" size={18} /> : <TrendingDown className="text-bearish" size={18} />}
            Price Forecast
          </h3>
          <p className="text-xs text-text-muted mt-1">Prophet model with 95% confidence intervals</p>
        </div>
        <div className="flex items-center space-x-1 bg-terminal-surface rounded-lg p-1">
          {FORECAST_DAYS.map((d) => (
            <button
              key={d.value}
              onClick={() => setDays(d.value)}
              className={clsx(
                'px-3 py-1 text-xs font-medium rounded transition-all',
                days === d.value
                  ? 'bg-accent-cyan text-black shadow-sm'
                  : 'text-text-muted hover:text-text-primary'
              )}
            >
              {d.label}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-terminal-border rounded w-1/3"></div>
          <div className="h-48 bg-terminal-border rounded"></div>
        </div>
      )}

      {!loading && (error || !priceForecast) && (
        <div className="text-center py-12">
          <Minus className="w-12 h-12 text-text-muted mx-auto mb-3" />
          <p className="text-text-muted text-sm">{error || 'Forecast unavailable'}</p>
          <p className="text-text-muted text-xs mt-1">Need at least 30 days of historical data</p>
        </div>
      )}

      {!loading && priceForecast && (
        <>
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div className="bg-terminal-surface p-3 rounded-lg">
              <p className="text-xs text-text-muted">Current</p>
              <p className="text-lg font-bold">{formatINR(priceForecast.last_price)}</p>
            </div>
            <div className="bg-terminal-surface p-3 rounded-lg">
              <p className="text-xs text-text-muted">{days}-Day Target</p>
              <p className={clsx("text-lg font-bold", changeColor)}>{formatINR(priceForecast.predicted_price)}</p>
            </div>
            <div className="bg-terminal-surface p-3 rounded-lg">
              <p className="text-xs text-text-muted">Expected</p>
              <p className={clsx("text-lg font-bold flex items-center gap-1", changeColor)}>
                <TrendIcon size={16} />
                {priceForecast.expected_change_pct >= 0 ? '+' : ''}{priceForecast.expected_change_pct?.toFixed(2)}%
              </p>
            </div>
            <div className="bg-terminal-surface p-3 rounded-lg">
              <p className="text-xs text-text-muted">Confidence</p>
              <p className="text-lg font-bold">95%</p>
            </div>
          </div>

          <div className="h-64 mb-4" style={{ minHeight: '256px', width: '100%' }}>
            {chartData.length > 0 && (
              <ResponsiveContainer width="100%" height={256}>
                <AreaChart data={chartData} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorUpperChart" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#f97316" stopOpacity={0.2} />
                      <stop offset="95%" stopColor="#f97316" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={10} domain={['auto', 'auto']} tickFormatter={(v) => `₹${(v/1000).toFixed(0)}K`} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f1f5f9' }} />
                  <Area type="monotone" dataKey="upper" stroke="#f97316" fill="url(#colorUpperChart)" connectNulls={false} />
                  <Area type="monotone" dataKey="lower" stroke="#64748b" fill="#1e293b" fillOpacity={0.5} connectNulls={false} />
                  <Line type="monotone" dataKey="price" stroke="#10b981" strokeWidth={2} dot={false} connectNulls={false} />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>

          <div className="grid grid-cols-3 gap-4 mb-4">
            <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3">
              <p className="text-xs text-green-400 font-medium">Upper Bound (+95%)</p>
              <p className="text-lg font-bold text-green-400">{formatINR(lastUpper)}</p>
            </div>
            <div className="bg-terminal-surface rounded-lg p-3">
              <p className="text-xs text-text-muted font-medium">Target Price</p>
              <p className="text-lg font-bold">{formatINR(priceForecast.predicted_price)}</p>
            </div>
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-xs text-red-400 font-medium">Lower Bound (-95%)</p>
              <p className="text-lg font-bold text-red-400">{formatINR(lastLower)}</p>
            </div>
          </div>

          <div className="p-3 bg-terminal-surface rounded-lg flex items-start gap-2">
            <Info size={16} className="text-accent-cyan flex-shrink-0 mt-0.5" />
            <p className="text-xs text-text-secondary">
              {priceForecast.trend_interpretation}. Not financial advice.
            </p>
          </div>

          {forecast.volatility_forecast && !forecast.volatility_forecast.error && (
            <div className="mt-4 pt-4 border-t border-terminal-border">
              <h4 className="text-sm font-semibold flex items-center gap-2 mb-3">
                <AlertTriangle size={14} className="text-accent-gold" />
                GARCH Volatility Forecast
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div className="bg-terminal-surface p-3 rounded-lg">
                  <p className="text-xs text-text-muted">Current Vol</p>
                  <p className="text-lg font-bold">{forecast.volatility_forecast.current_volatility?.toFixed(1)}%</p>
                </div>
                <div className="bg-terminal-surface p-3 rounded-lg">
                  <p className="text-xs text-text-muted">Forecast Vol</p>
                  <p className="text-lg font-bold text-accent-gold">{forecast.volatility_forecast.mean_forecast_vol?.toFixed(1)}%</p>
                </div>
                <div className="bg-terminal-surface p-3 rounded-lg">
                  <p className="text-xs text-text-muted">Status</p>
                  <p className="text-sm font-medium">{forecast.volatility_forecast.interpretation?.split(' - ')[0]}</p>
                </div>
                {forecast.risk_metrics && !forecast.risk_metrics.error && (
                  <div className="bg-terminal-surface p-3 rounded-lg">
                    <p className="text-xs text-text-muted">VaR (95%)</p>
                    <p className="text-lg font-bold text-bearish">{forecast.risk_metrics.var_daily?.toFixed(2)}%</p>
                  </div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
