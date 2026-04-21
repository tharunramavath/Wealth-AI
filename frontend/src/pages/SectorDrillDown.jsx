import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, Tooltip, PieChart, Pie, Cell, BarChart, Bar } from 'recharts';
import { ArrowLeft, TrendingUp, TrendingDown, Activity, AlertTriangle, Volume2, Target, RefreshCw, ArrowUpRight, ArrowDownRight } from 'lucide-react';

const WEIGHTAGE_COLORS = ['#06b6d4', '#10b981', '#8b5cf6', '#f59e0b', '#ec4899', '#14b8a6', '#f97316', '#6366f1'];

export default function SectorDrillDown() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortConfig, setSortConfig] = useState({ key: 'weight', direction: 'desc' });
  const [activeTab, setActiveTab] = useState('performance');

  const fetchSectorData = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/sector/detail/${encodeURIComponent(ticker)}`);
      setData(response.data);
    } catch (err) {
      console.error("Failed to fetch sector data:", err);
      setData({ error: "Failed to load sector data" });
    }
    setLoading(false);
  }, [ticker]);

  useEffect(() => {
    if (ticker) {
      fetchSectorData();
    }
  }, [ticker, fetchSectorData]);

  const handleSort = (key) => {
    setSortConfig(prev => ({
      key,
      direction: prev.key === key && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  const sortedConstituents = React.useMemo(() => {
    if (!data?.constituents) return [];
    const sorted = [...data.constituents];
    sorted.sort((a, b) => {
      if (sortConfig.key === 'name') {
        return sortConfig.direction === 'asc' ? a.name.localeCompare(b.name) : b.name.localeCompare(a.name);
      }
      return sortConfig.direction === 'asc' ? a[sortConfig.key] - b[sortConfig.key] : b[sortConfig.key] - a[sortConfig.key];
    });
    return sorted;
  }, [data?.constituents, sortConfig]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin w-10 h-10 border-2 border-accent-cyan border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (data?.error || !data) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-red-400 font-medium">{data?.error || "Failed to load sector data"}</p>
        <button onClick={() => navigate(-1)} className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg">
          Go Back
        </button>
      </div>
    );
  }

  const metrics = data.metrics || {};
  const chartData = data.price_history?.map((p, i) => ({
    date: p.date,
    sector: p.return,
    benchmark: data.benchmark_history?.[i]?.return || 0
  })) || [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-terminal-hover rounded-lg transition-colors">
            <ArrowLeft size={20} className="text-text-secondary" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-text-primary">{data.sector_name}</h1>
            <p className="text-text-muted text-sm mt-1">Sector Drill-Down Analysis</p>
          </div>
        </div>
        <div className="flex items-center space-x-3">
          <span className="text-text-muted text-xs">
            Last updated: {data.generated_at}
          </span>
          <button onClick={fetchSectorData} className="p-2 hover:bg-terminal-hover rounded-lg transition-colors">
            <RefreshCw size={18} className="text-text-secondary" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className={`rounded-xl p-4 ${metrics.relative_return >= 0 ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-rose-500/10 border border-rose-500/20'}`}>
          <span className="text-text-muted text-xs uppercase tracking-wide">90D Return</span>
          <p className={`text-2xl font-bold mt-1 ${metrics.relative_return >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
            {metrics.relative_return >= 0 ? '+' : ''}{metrics.relative_return?.toFixed(2)}%
          </p>
          <span className="text-text-muted text-xs">vs Nifty 50</span>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <span className="text-text-muted text-xs uppercase tracking-wide">30D Return</span>
          <p className={`text-2xl font-bold mt-1 ${metrics.return_30d >= 0 ? 'text-bullish' : 'text-bearish'}`}>
            {metrics.return_30d >= 0 ? '+' : ''}{metrics.return_30d?.toFixed(2)}%
          </p>
          <span className="text-text-muted text-xs">vs benchmark</span>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <span className="text-text-muted text-xs uppercase tracking-wide">Volatility</span>
          <p className="text-2xl font-bold mt-1 text-amber-400">{metrics.volatility_30d?.toFixed(1)}%</p>
          <span className="text-text-muted text-xs">30D annualized</span>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <span className="text-text-muted text-xs uppercase tracking-wide">Constituents</span>
          <p className="text-2xl font-bold mt-1 text-cyan-400">{data.constituents?.length || 0}</p>
          <span className="text-text-muted text-xs">top weighted stocks</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 bg-terminal-card border border-terminal-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">Performance vs Benchmark</h3>
            <div className="flex items-center space-x-4 text-xs">
              <span className="flex items-center space-x-1.5">
                <span className="w-3 h-0.5 bg-cyan-400"></span>
                <span className="text-text-muted">{data.sector_name}</span>
              </span>
              <span className="flex items-center space-x-1.5">
                <span className="w-3 h-0.5 bg-slate-500"></span>
                <span className="text-text-muted">Nifty 50</span>
              </span>
            </div>
          </div>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      return (
                        <div className="bg-[#0f172a] border border-slate-600/50 rounded-lg p-3 shadow-2xl">
                          <p className="text-slate-400 text-xs mb-2">{label}</p>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between gap-4">
                              <span className="text-slate-400 text-xs flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                                Sector
                              </span>
                              <span className={`text-xs font-mono ${payload[0]?.value >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {payload[0]?.value >= 0 ? '+' : ''}{payload[0]?.value?.toFixed(2)}%
                              </span>
                            </div>
                            <div className="flex items-center justify-between gap-4">
                              <span className="text-slate-400 text-xs flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-slate-500"></span>
                                Benchmark
                              </span>
                              <span className={`text-xs font-mono ${payload[1]?.value >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {payload[1]?.value >= 0 ? '+' : ''}{payload[1]?.value?.toFixed(2)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line type="monotone" dataKey="sector" stroke="#06b6d4" strokeWidth={2} dot={false} name="Sector" />
                <Line type="monotone" dataKey="benchmark" stroke="#64748b" strokeWidth={1.5} strokeDasharray="4 4" dot={false} name="Benchmark" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-5">
          <h3 className="font-semibold text-text-primary mb-4">Sector Weightage</h3>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.weightage_data}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={75}
                  paddingAngle={2}
                  dataKey="weight"
                  nameKey="name"
                >
                  {data.weightage_data?.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={WEIGHTAGE_COLORS[index % WEIGHTAGE_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const item = payload[0].payload;
                      return (
                        <div className="bg-[#0f172a] border border-slate-600/50 rounded-lg p-2 shadow-xl">
                          <p className="text-white text-xs font-medium">{item.name}</p>
                          <p className="text-cyan-400 text-xs">{item.weight?.toFixed(1)}%</p>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 space-y-1.5 max-h-32 overflow-y-auto">
            {data.weightage_data?.slice(0, 5).map((item, index) => (
              <div key={item.ticker} className="flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: WEIGHTAGE_COLORS[index] }}></div>
                  <span className="text-text-secondary truncate max-w-[100px]">{item.name}</span>
                </div>
                <span className="text-text-primary font-mono">{item.weight?.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {data.volume_spikes?.length > 0 && (
        <div className="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 flex items-start space-x-3">
          <Volume2 className="text-amber-400 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="text-amber-400 font-medium">Volume Alert</h4>
            <p className="text-amber-400/80 text-sm mt-1">
              {data.volume_spikes.map(s => s.name).join(', ')} showing unusual volume activity
            </p>
          </div>
        </div>
      )}

      <div className="bg-terminal-card border border-terminal-border rounded-xl overflow-hidden">
        <div className="border-b border-terminal-border">
          <div className="flex">
            <button
              onClick={() => setActiveTab('constituents')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'constituents' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-text-muted hover:text-text-primary'}`}
            >
              Constituents
            </button>
            <button
              onClick={() => setActiveTab('contributors')}
              className={`px-6 py-3 text-sm font-medium transition-colors ${activeTab === 'contributors' ? 'text-cyan-400 border-b-2 border-cyan-400' : 'text-text-muted hover:text-text-primary'}`}
            >
              Top Contributors
            </button>
          </div>
        </div>

        {activeTab === 'constituents' && (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="text-left text-text-muted text-xs uppercase border-b border-terminal-border bg-terminal-surface/50">
                  <th className="px-4 py-3 font-medium cursor-pointer hover:text-text-primary" onClick={() => handleSort('name')}>
                    <div className="flex items-center space-x-1">
                      <span>Stock</span>
                      {sortConfig.key === 'name' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('weight')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>Weight</span>
                      {sortConfig.key === 'weight' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('current_price')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>LTP</span>
                      {sortConfig.key === 'current_price' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('daily_change')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>Change</span>
                      {sortConfig.key === 'daily_change' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('contribution')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>Contribution</span>
                      {sortConfig.key === 'contribution' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('volume_ratio')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>Volume</span>
                      {sortConfig.key === 'volume_ratio' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                  <th className="px-4 py-3 font-medium text-right">Status</th>
                  <th className="px-4 py-3 font-medium text-right cursor-pointer hover:text-text-primary" onClick={() => handleSort('momentum_20d')}>
                    <div className="flex items-center justify-end space-x-1">
                      <span>20D Mom</span>
                      {sortConfig.key === 'momentum_20d' && (sortConfig.direction === 'asc' ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />)}
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-terminal-border">
                {sortedConstituents.map((stock) => (
                  <tr key={stock.ticker} className="text-sm hover:bg-terminal-hover/30 transition-colors">
                    <td className="px-4 py-3">
                      <div>
                        <p className="text-text-primary font-medium">{stock.name}</p>
                        <p className="text-text-muted text-xs">{stock.ticker}</p>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-text-primary font-mono">{stock.weight?.toFixed(1)}%</span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className="text-text-primary font-mono">₹{stock.current_price?.toLocaleString()}</span>
                    </td>
                    <td className={`px-4 py-3 text-right font-mono ${stock.daily_change >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {stock.daily_change >= 0 ? '+' : ''}{stock.daily_change?.toFixed(2)}%
                    </td>
                    <td className={`px-4 py-3 text-right font-mono ${stock.contribution >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {stock.contribution >= 0 ? '+' : ''}{stock.contribution?.toFixed(3)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end space-x-2">
                        {stock.volume_signal === 'Spike' && (
                          <span className="px-1.5 py-0.5 bg-amber-500/20 text-amber-400 text-xs rounded">Spike</span>
                        )}
                        <span className={`font-mono ${stock.volume_ratio > 1.5 ? 'text-amber-400' : 'text-text-secondary'}`}>
                          {stock.volume_ratio?.toFixed(1)}x
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        stock.tech_status === 'Near High' ? 'bg-emerald-500/20 text-emerald-400' :
                        stock.tech_status === 'Near Low' ? 'bg-rose-500/20 text-rose-400' :
                        stock.tech_status === 'Breakout' ? 'bg-cyan-500/20 text-cyan-400' :
                        stock.tech_status === 'Selloff' ? 'bg-red-500/20 text-red-400' :
                        'bg-slate-500/20 text-slate-400'
                      }`}>
                        {stock.tech_status}
                      </span>
                    </td>
                    <td className={`px-4 py-3 text-right font-mono ${stock.momentum_20d >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {stock.momentum_20d >= 0 ? '+' : ''}{stock.momentum_20d?.toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'contributors' && (
          <div className="p-4">
            <div className="space-y-3">
              {data.top_contributors?.map((stock, idx) => (
                <div key={stock.ticker} className="bg-terminal-surface rounded-lg p-4 flex items-center justify-between">
                  <div className="flex items-center space-x-4">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                      idx === 0 ? 'bg-amber-500/20 text-amber-400' :
                      idx === 1 ? 'bg-slate-400/20 text-slate-300' :
                      'bg-orange-600/20 text-orange-400'
                    }`}>
                      {idx + 1}
                    </div>
                    <div>
                      <p className="text-text-primary font-medium">{stock.name}</p>
                      <p className="text-text-muted text-xs">{stock.ticker}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className={`text-lg font-bold font-mono ${stock.contribution >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {stock.contribution >= 0 ? '+' : ''}{stock.contribution?.toFixed(3)}
                    </p>
                    <p className="text-text-muted text-xs">points contribution</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-6 h-48">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.top_contributors?.map(s => ({ name: s.name.split(' ')[0], contribution: s.contribution }))} layout="vertical">
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.toFixed(1)} />
                  <YAxis type="category" dataKey="name" width={80} tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-[#0f172a] border border-slate-600/50 rounded-lg p-2 shadow-xl">
                            <p className="text-white text-xs">{payload[0].payload.name}</p>
                            <p className={`text-xs font-mono ${payload[0].value >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                              {payload[0].value >= 0 ? '+' : ''}{payload[0].value?.toFixed(3)}
                            </p>
                          </div>
                        );
                      }
                      return null;
                    }}
                  />
                  <Bar dataKey="contribution" radius={[0, 4, 4, 0]}>
                    {data.top_contributors?.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.contribution >= 0 ? '#10b981' : '#ef4444'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
