import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, ScatterChart, Scatter, ZAxis, LineChart, Line } from 'recharts';
import { PieChart as PieChartIcon, TrendingUp, TrendingDown, AlertTriangle, Info, Activity, Target, ArrowRight, ArrowUpRight, ArrowDownRight, RefreshCw, ChevronRight } from 'lucide-react';

const QUADRANT_COLORS = {
  "Leading": { bg: "bg-green-500/20", border: "border-green-500/50", text: "text-green-400", icon: "🟢" },
  "Improving": { bg: "bg-blue-500/20", border: "border-blue-500/50", text: "text-blue-400", icon: "🔵" },
  "Weakening": { bg: "bg-orange-500/20", border: "border-orange-500/50", text: "text-orange-400", icon: "🟠" },
  "Lagging": { bg: "bg-red-500/20", border: "border-red-500/50", text: "text-red-400", icon: "🔴" },
};

const BREADTH_COLORS = {
  "Bullish": { bg: "bg-green-500/20", text: "text-green-400", border: "border-green-500/30" },
  "Bearish": { bg: "bg-red-500/20", text: "text-red-400", border: "border-red-500/30" },
  "Neutral": { bg: "bg-yellow-500/20", text: "text-yellow-400", border: "border-yellow-500/30" },
};

export default function SectorOverview() {
  const [rotationData, setRotationData] = useState(null);
  const [, setPortfolioAllocation] = useState({ allocation: {}, holdings: [] });
  const [, setRiskProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const navigate = useNavigate();

  const fetchData = React.useCallback(async () => {
    setLoading(true);
    try {
      const [rotationRes, analyticsRes, riskRes] = await Promise.all([
        api.get('/sector/rotation'),
        api.get('/portfolio/analytics'),
        api.get('/onboarding/risk-profile')
      ]);
      
      setRotationData(rotationRes.data);
      setPortfolioAllocation({
        allocation: analyticsRes.data?.sector_allocation || {},
        holdings: analyticsRes.data?.holdings || [],
        diversificationScore: analyticsRes.data?.diversification_score || 0,
        volatility: analyticsRes.data?.volatility || 0,
      });
      setRiskProfile(riskRes.data);
      setLastUpdated(new Date());
    } catch (err) {
      console.error("Failed to fetch sector data:", err);
      setRotationData({ error: "Failed to load data" });
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin w-10 h-10 border-2 border-accent-cyan border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (rotationData?.error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-red-400 font-medium">{rotationData.error}</p>
        <button onClick={fetchData} className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors">
          Retry
        </button>
      </div>
    );
  }

  const rrgData = rotationData?.rrg_coordinates || [];
  const breadth = rotationData?.market_breadth || {};
  const quadrants = rotationData?.quadrants || {};
  const summary = rotationData?.summary || {};

  const rrgChartData = rrgData.map(s => ({
    name: s.name,
    x: s.rs_ratio * 100,
    y: s.momentum,
    return: s.relative_return,
    quadrant: s.quadrant,
    size: Math.abs(s.relative_return) * 3 + 50,
  }));

  const breadthHistory = breadth.history || [];

  const quadrantActions = {
    "Leading": { action: "Hold / Add", color: "text-green-400", desc: "Outperforming with momentum" },
    "Improving": { action: "Watch / Buy Early", color: "text-blue-400", desc: "Bottoming out; money flowing in" },
    "Weakening": { action: "Take Profits", color: "text-orange-400", desc: "Losing momentum despite outperformance" },
    "Lagging": { action: "Avoid / Reduce", color: "text-red-400", desc: "Underperforming; capital rotating out" },
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Sector Intelligence</h1>
          <p className="text-text-muted text-sm mt-1">Institutional-Grade Market Breadth & Rotation Analysis</p>
        </div>
        <div className="flex items-center space-x-3">
          {lastUpdated && (
            <span className="text-text-muted text-xs">
              Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button onClick={fetchData} className="p-2 hover:bg-terminal-hover rounded-lg transition-colors">
            <RefreshCw size={18} className="text-text-secondary" />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        <div className={`rounded-xl p-4 ${BREADTH_COLORS[breadth.signal || 'Neutral'].bg} border ${BREADTH_COLORS[breadth.signal || 'Neutral'].border}`}>
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-muted text-xs uppercase tracking-wide">Market Breadth</span>
            <Activity size={16} className={BREADTH_COLORS[breadth.signal || 'Neutral'].text} />
          </div>
          <p className={`text-2xl font-bold ${BREADTH_COLORS[breadth.signal || 'Neutral'].text}`}>
            {breadth.signal || 'Neutral'}
          </p>
          <div className="mt-2 flex items-center space-x-2 text-xs">
            <span className="text-bullish">{breadth.current?.advancing || 0} Advancing</span>
            <span className="text-text-muted">/</span>
            <span className="text-bearish">{breadth.current?.declining || 0} Declining</span>
          </div>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-muted text-xs uppercase tracking-wide">Leading Sectors</span>
            <Target size={16} className="text-green-400" />
          </div>
          <p className="text-2xl font-bold text-green-400">{summary.leading_count || 0}</p>
          <p className="text-text-muted text-xs mt-1">Strong momentum + outperformance</p>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-muted text-xs uppercase tracking-wide">Improving</span>
            <ArrowUpRight size={16} className="text-blue-400" />
          </div>
          <p className="text-2xl font-bold text-blue-400">{summary.improving_count || 0}</p>
          <p className="text-text-muted text-xs mt-1">Early rotation; recovery phase</p>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-4">
          <div className="flex items-center justify-between mb-2">
            <span className="text-text-muted text-xs uppercase tracking-wide">Risk Sectors</span>
            <AlertTriangle size={16} className="text-orange-400" />
          </div>
          <p className="text-2xl font-bold text-orange-400">
            {(summary.weakening_count || 0) + (summary.lagging_count || 0)}
          </p>
          <p className="text-text-muted text-xs mt-1">Weakening/Lagging sectors</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-terminal-card border border-terminal-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-text-primary">Relative Rotation Graph (RRG)</h3>
            <div className="flex items-center space-x-4 text-xs">
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-green-400"></span>
                <span className="text-text-muted">Leading</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                <span className="text-text-muted">Improving</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-orange-400"></span>
                <span className="text-text-muted">Weakening</span>
              </span>
              <span className="flex items-center space-x-1">
                <span className="w-2 h-2 rounded-full bg-red-400"></span>
                <span className="text-text-muted">Lagging</span>
              </span>
            </div>
          </div>
          <div className="relative h-80">
            <div className="absolute inset-0 border-l border-terminal-border border-b border-terminal-border">
              <div className="absolute left-1/2 top-0 h-full w-px bg-terminal-border/50 -translate-x-1/2"></div>
              <div className="absolute top-1/2 left-0 w-full h-px bg-terminal-border/50 -translate-y-1/2"></div>
              <span className="absolute top-1 left-1/2 text-[10px] text-text-muted -translate-x-1/2">Leading</span>
              <span className="absolute top-1 right-1/2 text-[10px] text-text-muted translate-x-1/2">Weakening</span>
              <span className="absolute bottom-1 left-1/2 text-[10px] text-text-muted -translate-x-1/2">Lagging</span>
              <span className="absolute bottom-1 right-1/2 text-[10px] text-text-muted translate-x-1/2">Improving</span>
            </div>
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 20, right: 20, bottom: 20, left: 20 }}>
                <XAxis type="number" dataKey="x" name="RS-Ratio" domain={['dataMin - 5', 'dataMax + 5']} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.toFixed(0)} />
                <YAxis type="number" dataKey="y" name="RS-Momentum" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.toFixed(1)} />
                <ZAxis type="number" dataKey="size" range={[50, 400]} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (active && payload && payload.length) {
                      const data = payload[0].payload;
                      const quadColor = 
                        data.quadrant === 'Leading' ? '#10b981' :
                        data.quadrant === 'Improving' ? '#3b82f6' :
                        data.quadrant === 'Weakening' ? '#f97316' : '#ef4444';
                      return (
                        <div className="bg-[#0f172a] border border-slate-600/50 rounded-lg p-3 shadow-2xl min-w-[160px]">
                          <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-700/50">
                            <span className="font-semibold text-white text-sm">{data.name}</span>
                          </div>
                          <div className="space-y-1.5">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full" style={{ backgroundColor: quadColor }}></span>
                                Quadrant
                              </span>
                              <span className="font-medium text-xs" style={{ color: quadColor }}>{data.quadrant}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs">RS-Ratio</span>
                              <span className="text-slate-200 text-xs font-mono">{data.x.toFixed(3)}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs">RS-Momentum</span>
                              <span className={`text-xs font-mono ${data.y >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {data.y >= 0 ? '+' : ''}{data.y.toFixed(2)}
                              </span>
                            </div>
                            <div className="flex items-center justify-between pt-1 border-t border-slate-700/50 mt-1">
                              <span className="text-slate-400 text-xs">Rel. Return</span>
                              <span className={`text-xs font-mono font-semibold ${data.return >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                                {data.return >= 0 ? '+' : ''}{data.return.toFixed(2)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Scatter data={rrgChartData}>
                  {rrgChartData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={
                        entry.quadrant === 'Leading' ? '#10b981' :
                        entry.quadrant === 'Improving' ? '#3b82f6' :
                        entry.quadrant === 'Weakening' ? '#f97316' : '#ef4444'
                      }
                      opacity={0.8}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-terminal-card border border-terminal-border rounded-xl p-5">
          <h3 className="font-semibold text-text-primary mb-4">Breadth Trend</h3>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={breadthHistory}>
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => v.slice(5)} />
                <YAxis domain={[0, 100]} tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={(v) => `${v}%`} />
                <Tooltip
                  content={({ active, payload, label }) => {
                    if (active && payload && payload.length) {
                      const breadthVal = payload.find(p => p.dataKey === 'breadth_pct');
                      const advVal = payload.find(p => p.dataKey === 'advancing');
                      const decVal = payload.find(p => p.dataKey === 'declining');
                      const breadthPct = breadthVal?.value || 0;
                      const signalColor = breadthPct > 60 ? '#10b981' : breadthPct < 40 ? '#ef4444' : '#f59e0b';
                      return (
                        <div className="bg-[#0f172a] border border-slate-600/50 rounded-lg p-3 shadow-2xl min-w-[150px]">
                          <div className="flex items-center justify-between mb-2 pb-2 border-b border-slate-700/50">
                            <span className="text-slate-300 text-xs">{label}</span>
                            <span className="text-xs font-medium px-2 py-0.5 rounded-full" style={{ backgroundColor: `${signalColor}20`, color: signalColor }}>
                              {breadthPct > 60 ? 'Bullish' : breadthPct < 40 ? 'Bearish' : 'Neutral'}
                            </span>
                          </div>
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-sm bg-cyan-400"></span>
                                Breadth
                              </span>
                              <span className="text-cyan-400 text-xs font-mono font-semibold">{breadthPct.toFixed(1)}%</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-sm bg-emerald-400"></span>
                                Advancing
                              </span>
                              <span className="text-emerald-400 text-xs font-mono">{advVal?.value}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-slate-400 text-xs flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-sm bg-rose-400"></span>
                                Declining
                              </span>
                              <span className="text-rose-400 text-xs font-mono">{decVal?.value}</span>
                            </div>
                          </div>
                        </div>
                      );
                    }
                    return null;
                  }}
                />
                <Line type="monotone" dataKey="breadth_pct" stroke="#06b6d4" strokeWidth={2} dot={{ fill: '#06b6d4', r: 3 }} name="Breadth %" />
                <Bar dataKey="advancing" fill="#10b981" opacity={0.3} name="Advancing" />
                <Bar dataKey="declining" fill="#ef4444" opacity={0.3} name="Declining" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="bg-terminal-card border border-terminal-border rounded-xl p-5">
        <h3 className="font-semibold text-text-primary mb-4">Sector Rotation Matrix</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(quadrantActions).map(([quadrant, info]) => {
            const sectors = quadrants[quadrant] || [];
            return (
              <div key={quadrant} className={`rounded-xl p-4 ${QUADRANT_COLORS[quadrant].bg} border ${QUADRANT_COLORS[quadrant].border}`}>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">{QUADRANT_COLORS[quadrant].icon}</span>
                    <span className={`font-semibold ${QUADRANT_COLORS[quadrant].text}`}>{quadrant}</span>
                  </div>
                  <span className={`text-xs font-medium ${info.color}`}>{info.action}</span>
                </div>
                <p className="text-text-muted text-xs mb-3">{info.desc}</p>
                {sectors.length > 0 ? (
                  <div className="space-y-2">
                    {sectors.slice(0, 3).map((sector) => (
                      <div 
                        key={sector.ticker} 
                        className="flex items-center justify-between text-sm cursor-pointer hover:bg-black/10 rounded px-1 -mx-1 transition-colors"
                        onClick={(e) => { e.stopPropagation(); navigate(`/sector/${encodeURIComponent(sector.ticker)}`); }}
                      >
                        <span className="text-text-primary truncate">{sector.name}</span>
                        <span className={`font-mono ${sector.relative_return >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                          {sector.relative_return >= 0 ? '+' : ''}{sector.relative_return?.toFixed(1)}%
                        </span>
                      </div>
                    ))}
                    {sectors.length > 3 && (
                      <span className="text-text-muted text-xs">+{sectors.length - 3} more</span>
                    )}
                  </div>
                ) : (
                  <p className="text-text-muted text-xs italic">No sectors in this quadrant</p>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="bg-terminal-card border border-terminal-border rounded-xl p-5">
        <h3 className="font-semibold text-text-primary mb-4">Institutional Sector View</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-text-muted text-xs uppercase border-b border-terminal-border">
                <th className="pb-3 font-medium">Sector</th>
                <th className="pb-3 font-medium">Quadrant</th>
                <th className="pb-3 font-medium text-right">Action</th>
                <th className="pb-3 font-medium text-right">Sector Return</th>
                <th className="pb-3 font-medium text-right">vs Benchmark</th>
                <th className="pb-3 font-medium text-right">RS Ratio</th>
                <th className="pb-3 font-medium text-right">Momentum</th>
                <th className="pb-3 font-medium text-right">Weight Adj.</th>
                <th className="pb-3 font-medium">Trend</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-terminal-border">
              {rrgData.sort((a, b) => b.relative_return - a.relative_return).map((sector) => {
                const colors = QUADRANT_COLORS[sector.quadrant];
                const action = quadrantActions[sector.quadrant];
                
                // Dynamic Weight Suggestion Logic
                const weightSuggest = sector.quadrant === "Leading" ? { label: "Overweight", val: "+2.5%", color: "text-green-400" } :
                                    sector.quadrant === "Improving" ? { label: "Accumulate", val: "+1.5%", color: "text-blue-400" } :
                                    sector.quadrant === "Weakening" ? { label: "Trim", val: "-1.0%", color: "text-orange-400" } :
                                    { label: "Underweight", val: "-4.0%", color: "text-red-400" };

                return (
                  <tr 
                    key={sector.ticker} 
                    className="text-sm hover:bg-terminal-hover/50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/sector/${encodeURIComponent(sector.ticker)}`)}
                  >
                    <td className="py-3">
                      <div className="flex items-center space-x-2">
                        <span className="text-text-primary font-medium">{sector.name}</span>
                        <ChevronRight size={14} className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
                      </div>
                    </td>
                    <td className="py-3">
                      <span className={`inline-flex items-center space-x-1 px-2 py-1 rounded-full text-xs ${colors.bg} ${colors.text}`}>
                        <span>{colors.icon}</span>
                        <span>{sector.quadrant}</span>
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <span className={`text-xs font-medium ${action.color}`}>{action.action}</span>
                    </td>
                    <td className={`py-3 text-right font-mono ${sector.sector_return >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {sector.sector_return >= 0 ? '+' : ''}{sector.sector_return?.toFixed(2)}%
                    </td>
                    <td className={`py-3 text-right font-mono ${sector.relative_return >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {sector.relative_return >= 0 ? '+' : ''}{sector.relative_return?.toFixed(2)}%
                    </td>
                    <td className="py-3 text-right text-text-secondary font-mono">
                      {sector.rs_ratio?.toFixed(4)}
                    </td>
                    <td className={`py-3 text-right font-mono ${sector.momentum >= 0 ? 'text-bullish' : 'text-bearish'}`}>
                      {sector.momentum >= 0 ? '+' : ''}{sector.momentum?.toFixed(2)}
                    </td>
                    <td className="py-3 text-right">
                      <div className="flex flex-col items-end">
                        <span className={`text-[10px] uppercase font-bold ${weightSuggest.color}`}>{weightSuggest.label}</span>
                        <span className="text-xs font-mono text-text-primary">{weightSuggest.val}</span>
                      </div>
                    </td>
                    <td className="py-3">
                      {sector.mom_change > 0 ? (
                        <ArrowUpRight size={16} className="text-green-400" />
                      ) : sector.mom_change < 0 ? (
                        <ArrowDownRight size={16} className="text-red-400" />
                      ) : (
                        <ArrowRight size={16} className="text-text-muted" />
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-gradient-to-r from-accent-purple/10 to-accent-cyan/10 border border-terminal-border rounded-xl p-5">
        <div className="flex items-start space-x-4">
          <div className="w-10 h-10 rounded-lg bg-accent-purple/20 flex items-center justify-center flex-shrink-0">
            <Info size={20} className="text-accent-purple" />
          </div>
          <div>
            <h4 className="text-text-primary font-semibold">Institutional Rotation Insight</h4>
            <p className="text-text-muted text-sm mt-1 leading-relaxed">
              {summary.leading_count > 0 && summary.improving_count > 0 ? (
                <>The Indian market shows healthy rotation with <span className="text-green-400">{summary.leading_count} leading</span> and <span className="text-blue-400">{summary.improving_count} improving</span> sectors. Smart money is diversifying while maintaining exposure to outperformers.</>
              ) : summary.weakening_count + summary.lagging_count > 2 ? (
                <>Market showing signs of sector rotation away from laggards. Consider reducing <span className="text-red-400">{summary.lagging_count} lagging</span> sectors and monitoring <span className="text-orange-400">{summary.weakening_count} weakening</span> positions for profit-taking opportunities.</>
              ) : (
                <>Current breadth suggests a mixed sector environment. Focus on sectors with positive relative strength and monitor momentum shifts for early rotation signals.</>
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
