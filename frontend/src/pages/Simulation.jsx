import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import { Plus, Play, Trash2, BarChart2, RefreshCw, AlertTriangle, Activity, Target, TrendingUp, GitBranch, Shield, Zap, Sparkles, Cpu, Layers, Info, History } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid, Legend, BarChart, Bar, Cell } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { cn } from '../lib/utils';
import { useTheme } from '../hooks/use-theme';

const COLORS = {
  bullish: '#10b981',
  bearish: '#ef4444',
  brand: '#3b82f6',
  cyan: '#06b6d4',
  purple: '#8b5cf6',
  gold: '#f59e0b',
  slate: '#64748b'
};

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <Card className="border-none shadow-2xl bg-card/90 backdrop-blur-xl p-4 animate-in zoom-in-95 duration-200">
        <p className="text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-2 border-b border-border pb-1">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry, index) => (
            <div key={index} className="flex items-center justify-between space-x-4">
               <div className="flex items-center">
                 <div className="w-1.5 h-1.5 rounded-full mr-2" style={{ backgroundColor: entry.color }}></div>
                 <span className="text-xs font-bold text-foreground opacity-80">{entry.name}</span>
               </div>
               <span className="text-xs font-black text-foreground tabular-nums">
                 {typeof entry.value === 'number' ? 
                    (entry.name.includes('%') || entry.name.includes('Return') ? 
                      `${entry.value > 0 ? '+' : ''}${entry.value.toFixed(2)}%` : 
                      `₹${entry.value.toLocaleString()}`) : 
                    entry.value}
               </span>
            </div>
          ))}
        </div>
      </Card>
    );
  }
  return null;
};

export default function Simulation() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedScenario, setSelectedScenario] = useState(null);
  const [backtestResult, setBacktestResult] = useState(null);
  const [monteCarloResult, setMonteCarloResult] = useState(null);
  const [stressResult, setStressResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [runningAnalysis, setRunningAnalysis] = useState(false);
  const [period, setPeriod] = useState('6M');
  const [, setHorizon] = useState(90);
  const [stressScenario, setStressScenario] = useState('2008_CRISIS');
  const [activeTab, setActiveTab] = useState('backtest');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newScenario, setNewScenario] = useState({ name: '', description: '', proposed_holdings: [] });
  const [tickerInput, setTickerInput] = useState({ ticker: '', quantity: '', avg_price: '' });
  const [tickerSuggestions, setTickerSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const { theme } = useTheme();

  const loadScenarios = React.useCallback(() => {
    setLoading(true);
    api.get('/simulation/scenarios').then(r => {
      setScenarios(r.data);
    }).catch(() => {})
    .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadScenarios(); }, [loadScenarios]);

  const searchTickers = async (query) => {
    if (query.length < 2) { setTickerSuggestions([]); return; }
    try {
      const res = await api.get(`/ticker/search?q=${encodeURIComponent(query)}`);
      setTickerSuggestions(res.data);
    } catch { setTickerSuggestions([]); }
  };

  const handleTickerChange = (e) => {
    const val = e.target.value;
    setTickerInput({ ...tickerInput, ticker: val });
    setShowSuggestions(true);
    searchTickers(val);
  };

  const selectSuggestion = (s) => {
    setTickerInput({ ...tickerInput, ticker: s.symbol });
    setTickerSuggestions([]);
    setShowSuggestions(false);
  };

  const addHolding = () => {
    if (!tickerInput.ticker || !tickerInput.quantity || !tickerInput.avg_price) return;
    setNewScenario({
      ...newScenario,
      proposed_holdings: [...newScenario.proposed_holdings, {
        ticker: tickerInput.ticker.toUpperCase(),
        quantity: parseFloat(tickerInput.quantity),
        avg_price: parseFloat(tickerInput.avg_price)
      }]
    });
    setTickerInput({ ticker: '', quantity: '', avg_price: '' });
  };

  const removeHolding = (idx) => {
    const updated = newScenario.proposed_holdings.filter((_, i) => i !== idx);
    setNewScenario({ ...newScenario, proposed_holdings: updated });
  };

  const createScenario = async () => {
    if (!newScenario.name || newScenario.proposed_holdings.length === 0) {
      toast.error('Identity and assets required for matrix formation');
      return;
    }
    try {
      await api.post('/simulation/scenario/create', {
        name: newScenario.name,
        description: newScenario.description,
        proposed_holdings: newScenario.proposed_holdings,
        is_nba_based: false
      });
      toast.success('Strategy Matrix Synchronized');
      setShowCreateForm(false);
      setNewScenario({ name: '', description: '', proposed_holdings: [] });
      loadScenarios();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Matrix error');
    }
  };

  const runAllAnalyses = async (scenarioId) => {
    setRunningAnalysis(true);
    try {
      toast.loading('Computing Neural Paths...', { id: 'sim' });
      const [backtestRes, mcRes, stressRes] = await Promise.all([
        api.post(`/simulation/scenario/${scenarioId}/backtest?period=${period}`),
        api.post(`/simulation/scenario/${scenarioId}/monte-carlo?horizon_days=90`),
        api.post(`/simulation/scenario/${scenarioId}/stress-test?scenario_name=${stressScenario}`)
      ]);
      
      setBacktestResult(backtestRes.data);
      setMonteCarloResult(mcRes.data);
      setStressResult(stressRes.data);
      setSelectedScenario(scenarios.find(s => s.scenario_id === scenarioId));
      toast.success('Simulation Matrix Resolved!', { id: 'sim' });
    } catch {
      toast.error('Engine Compute Error', { id: 'sim' });
    }
    setRunningAnalysis(false);
  };

  const runStressTestOnly = async () => {
    if (!selectedScenario) return;
    setRunningAnalysis(true);
    try {
      const res = await api.post(`/simulation/scenario/${selectedScenario.scenario_id}/stress-test?scenario_name=${stressScenario}`);
      setStressResult(res.data);
    } catch {
      toast.error('Stress vector failed');
    }
    setRunningAnalysis(false);
  };

  const deleteScenario = async (scenarioId) => {
    try {
      await api.delete(`/simulation/scenario/${scenarioId}`);
      toast.success('Matrix Decommissioned');
      loadScenarios();
      if (selectedScenario?.scenario_id === scenarioId) {
        setSelectedScenario(null);
        setBacktestResult(null);
        setMonteCarloResult(null);
        setStressResult(null);
      }
    } catch {
      toast.error('Decommission error');
    }
  };

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center space-y-4">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
          <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest animate-pulse">Initializing Lab Environments...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight uppercase">What-If Lab</h1>
          <p className="text-muted-foreground font-semibold text-sm mt-2 uppercase tracking-tight flex items-center">
            <Sparkles size={14} className="mr-2 text-primary" />
            Simulate tectonic portfolio shifts and stress-test alpha strategies.
          </p>
        </div>
        <Button
          onClick={() => setShowCreateForm(true)}
          className="rounded-2xl h-14 px-8 font-black uppercase tracking-widest shadow-xl shadow-primary/20 group"
        >
          <Plus size={18} className="mr-2 group-hover:scale-125 transition-transform" />
          <span>New Matrix</span>
        </Button>
      </div>

      {showCreateForm && (
        <Card className="rounded-[3rem] border-none shadow-2xl shadow-black/5 p-10 animate-in slide-in-from-top-4 duration-500 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-10 opacity-[0.02] group-hover:rotate-12 transition-all duration-700">
             <Layers size={150} />
          </div>
          <h3 className="text-2xl font-black text-foreground uppercase tracking-tight mb-10">Matrix Configuration</h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-10">
            <div className="space-y-8">
              <div className="space-y-2">
                <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Instance Label</label>
                <Input
                  value={newScenario.name}
                  onChange={e => setNewScenario({ ...newScenario, name: e.target.value })}
                  className="h-14 rounded-2xl bg-accent/30 border-none text-base font-black focus-visible:ring-primary/20"
                  placeholder="e.g. 2026 ALPHA PIVOT"
                />
              </div>
              <div className="space-y-2">
                <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Hypothesis Context</label>
                <textarea
                  value={newScenario.description}
                  onChange={e => setNewScenario({ ...newScenario, description: e.target.value })}
                  className="w-full bg-accent/30 border-none rounded-2xl p-5 text-sm text-foreground font-medium focus:ring-4 focus:ring-primary/10 outline-none transition-all h-32 resize-none"
                  placeholder="Establish the logic for this asset deployment..."
                />
              </div>
            </div>

            <div className="bg-accent/20 rounded-[2.5rem] p-8 border border-border/50 relative">
              <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-8">Asset Assembly</h4>
              <div className="flex flex-col space-y-6">
                <div className="flex gap-3">
                  <div className="relative flex-[2]">
                    <Input
                      value={tickerInput.ticker}
                      onChange={handleTickerChange}
                      className="h-12 rounded-xl bg-background border-border font-black uppercase text-xs"
                      placeholder="Ticker"
                    />
                    {showSuggestions && tickerSuggestions.length > 0 && (
                      <div className="absolute z-50 w-full mt-2 bg-card border border-border rounded-xl shadow-2xl max-h-48 overflow-hidden animate-in fade-in duration-200">
                        {tickerSuggestions.map(s => (
                          <div key={s.symbol} onClick={() => selectSuggestion(s)}
                               className="px-4 py-3 hover:bg-accent cursor-pointer text-[10px] font-black text-foreground border-b border-border last:border-b-0 flex justify-between uppercase">
                            <span>{s.symbol}</span>
                            <span className="text-muted-foreground opacity-60">{s.name.slice(0, 15)}</span>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                  <Input
                    type="number"
                    value={tickerInput.quantity}
                    onChange={e => setTickerInput({ ...tickerInput, quantity: e.target.value })}
                    className="flex-1 h-12 rounded-xl bg-background border-border font-black text-xs tabular-nums"
                    placeholder="Qty"
                  />
                  <Input
                    type="number"
                    value={tickerInput.avg_price}
                    onChange={e => setTickerInput({ ...tickerInput, avg_price: e.target.value })}
                    className="flex-1 h-12 rounded-xl bg-background border-border font-black text-xs tabular-nums"
                    placeholder="Cost"
                  />
                  <Button onClick={addHolding} size="icon" className="h-12 w-12 rounded-xl shadow-lg shadow-primary/20 hover:scale-110 active:scale-95 transition-all">
                    <Plus size={20} />
                  </Button>
                </div>

                <div className="max-h-[220px] overflow-y-auto custom-scrollbar space-y-3 pr-2">
                  {newScenario.proposed_holdings.length === 0 ? (
                    <div className="py-14 text-center border-2 border-dashed border-border/50 rounded-3xl opacity-40">
                       <p className="text-[10px] font-black uppercase text-muted-foreground tracking-widest">Assembly Grid Empty</p>
                    </div>
                  ) : (
                    newScenario.proposed_holdings.map((h, idx) => (
                      <div key={idx} className="flex items-center justify-between bg-background px-5 py-4 rounded-2xl border border-border group shadow-sm hover:border-primary/30 transition-all">
                        <div className="flex items-center space-x-4">
                           <div className="w-10 h-10 rounded-xl bg-accent flex items-center justify-center text-[10px] font-black text-primary border border-border">{h.ticker.slice(0, 2)}</div>
                           <div>
                             <span className="text-xs font-black text-foreground uppercase block leading-none mb-1">{h.ticker}</span>
                             <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter">{h.quantity} units @ ₹{h.avg_price}</span>
                           </div>
                        </div>
                        <Button variant="ghost" size="icon" onClick={() => removeHolding(idx)} className="text-muted-foreground hover:text-destructive transition-all opacity-0 group-hover:opacity-100">
                          <Trash2 size={16} />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end space-x-4">
            <Button variant="ghost" onClick={() => setShowCreateForm(false)} className="rounded-xl font-black uppercase tracking-widest text-[10px]">Cancel Matrix</Button>
            <Button onClick={createScenario} className="rounded-xl px-10 h-12 font-black uppercase tracking-widest shadow-xl shadow-primary/20 group">
              <Sparkles size={16} className="mr-2 group-hover:rotate-12 transition-transform" />
              Initialize Strategy
            </Button>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left: Scenarios Panel */}
        <div className="lg:col-span-4 space-y-6">
          <div className="flex items-center justify-between px-2">
            <h2 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Strategy Environments</h2>
            <Badge variant="secondary" className="px-2 py-0.5 font-black text-[9px]">{scenarios.length} Matrices</Badge>
          </div>
          
          <div className="space-y-4">
            {scenarios.length === 0 ? (
              <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 p-12 text-center flex flex-col items-center bg-accent/5">
                 <GitBranch size={48} className="text-muted-foreground opacity-20 mb-6 animate-pulse" />
                 <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Awaiting signal definitions</p>
              </Card>
            ) : (
              scenarios.map(scenario => (
                <Card
                  key={scenario.scenario_id}
                  onClick={() => { setSelectedScenario(scenario); setBacktestResult(null); setMonteCarloResult(null); setStressResult(null); }}
                  className={cn("rounded-[2rem] p-8 cursor-pointer transition-all border-2 relative group overflow-hidden", 
                    selectedScenario?.scenario_id === scenario.scenario_id
                      ? 'border-primary shadow-xl shadow-primary/10 translate-x-2'
                      : 'border-transparent hover:border-border hover:bg-accent/20'
                  )}
                >
                  <div className="flex justify-between items-start mb-6">
                    <div>
                      <h3 className="text-sm font-black text-foreground uppercase tracking-tight leading-none mb-2">{scenario.name}</h3>
                      <p className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter line-clamp-1 opacity-60">{scenario.description || 'Raw Strategy Matrix'}</p>
                    </div>
                    {scenario.is_nba_based && (
                      <Badge variant="bullish" className="px-2 py-0.5 text-[8px] font-black uppercase">Neural</Badge>
                    )}
                  </div>

                  <div className="flex items-center justify-between mt-8 relative z-10">
                    <div className="flex -space-x-2">
                       {(scenario.proposed_holdings || []).slice(0, 4).map((h, i) => (
                         <div key={i} className="w-8 h-8 rounded-xl bg-accent border-2 border-card flex items-center justify-center text-[9px] font-black text-foreground shadow-sm uppercase">
                            {h.ticker.slice(0, 2)}
                         </div>
                       ))}
                       {(scenario.proposed_holdings || []).length > 4 && (
                         <div className="w-8 h-8 rounded-xl bg-primary text-primary-foreground border-2 border-card flex items-center justify-center text-[9px] font-black shadow-sm">
                            +{(scenario.proposed_holdings || []).length - 4}
                         </div>
                       )}
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={(e) => { e.stopPropagation(); deleteScenario(scenario.scenario_id); }}
                      className="rounded-xl text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all opacity-0 group-hover:opacity-100 h-8 w-8"
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>

        {/* Right: Analysis Dashboard */}
        <div className="lg:col-span-8">
          {selectedScenario ? (
            <div className="space-y-8 animate-in fade-in slide-in-from-right-4 duration-500">
              <Card className="rounded-[3rem] border-none shadow-2xl shadow-black/5 overflow-hidden border-2 border-primary/5">
                <CardHeader className="px-10 py-8 border-b border-border/50 bg-card flex flex-col md:flex-row md:items-center justify-between gap-8">
                  <div className="flex items-center space-x-6">
                     <div className="w-16 h-16 rounded-[2rem] bg-primary/10 flex items-center justify-center text-primary border border-primary/20 shadow-inner">
                        <Cpu size={32} />
                     </div>
                     <div>
                       <h2 className="text-2xl font-black text-foreground uppercase tracking-tight">{selectedScenario.name}</h2>
                       <p className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] flex items-center mt-1">
                         <Activity size={12} className="mr-2 text-primary" /> Active Compute Instance
                       </p>
                     </div>
                  </div>
                  
                  <div className="flex items-center space-x-4">
                    <div className="flex items-center bg-accent/30 border border-border/50 rounded-2xl px-4 py-2">
                       <span className="text-[10px] font-black text-muted-foreground mr-3 uppercase tracking-widest">Backtest:</span>
                       <select
                        value={period}
                        onChange={e => setPeriod(e.target.value)}
                        className="bg-transparent text-xs font-black text-foreground outline-none cursor-pointer pr-1 uppercase"
                      >
                        <option value="1M">1 Month</option>
                        <option value="3M">Quarter</option>
                        <option value="6M">Semi-Annual</option>
                        <option value="1Y">Annual</option>
                      </select>
                    </div>
                    
                    <Button
                      onClick={() => runAllAnalyses(selectedScenario.scenario_id)}
                      disabled={runningAnalysis}
                      className="rounded-2xl h-12 px-8 font-black uppercase tracking-widest shadow-xl shadow-primary/20 group h-14"
                    >
                      {runningAnalysis ? <RefreshCw className="animate-spin mr-3" size={18} /> : <Play className="mr-3 group-hover:scale-125 transition-transform" size={18} />}
                      {runningAnalysis ? 'Computing...' : 'Launch Matrix'}
                    </Button>
                  </div>
                </CardHeader>
                
                <div className="flex border-b border-border/50 bg-accent/10 px-4">
                  {[
                    { id: 'backtest', label: 'History Delta', icon: History },
                    { id: 'montecarlo', label: 'Probability', icon: Target },
                    { id: 'stress', label: 'Crisis Vectors', icon: AlertTriangle },
                    { id: 'risk', label: 'Risk Profile', icon: Shield }
                  ].map(tab => {
                    const Icon = tab.icon;
                    const isActive = activeTab === tab.id;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => setActiveTab(tab.id)}
                        className={cn("flex-1 px-6 py-5 text-[10px] font-black uppercase tracking-widest transition-all flex items-center justify-center space-x-3 relative group", 
                          isActive 
                            ? 'text-primary bg-background' 
                            : 'text-muted-foreground hover:text-foreground'
                        )}
                      >
                        {isActive && <div className="absolute bottom-0 left-4 right-4 h-1 bg-primary rounded-t-full" />}
                        <Icon size={16} className={cn("transition-transform group-hover:scale-110", isActive ? "text-primary" : "text-muted-foreground")} />
                        <span className="hidden sm:inline">{tab.label}</span>
                      </button>
                    );
                  })}
                </div>

                <div className="p-10 min-h-[500px]">
                  {activeTab === 'backtest' && (
                    <BacktestTab result={backtestResult} loading={runningAnalysis} theme={theme} />
                  )}
                  {activeTab === 'montecarlo' && (
                    <MonteCarloTab result={monteCarloResult} loading={runningAnalysis} horizon={90} theme={theme} />
                  )}
                  {activeTab === 'stress' && (
                    <StressTestTab result={stressResult} loading={runningAnalysis} scenario={stressScenario} setScenario={setStressScenario} onScenarioChange={runStressTestOnly} theme={theme} />
                  )}
                  {activeTab === 'risk' && (
                    <RiskAnalysisTab analysis={backtestResult} loading={runningAnalysis} theme={theme} />
                  )}
                </div>
              </Card>
            </div>
          ) : (
            <Card className="rounded-[3rem] border-none shadow-2xl shadow-black/5 h-[650px] flex flex-col items-center justify-center text-center p-16 bg-accent/5">
               <div className="relative mb-10">
                 <div className="w-28 h-28 bg-accent rounded-[45px] flex items-center justify-center border border-border shadow-inner group-hover:scale-110 transition-transform duration-700">
                   <Activity size={56} className="text-muted-foreground/20" />
                 </div>
                 <div className="absolute top-0 right-0 w-10 h-10 bg-primary rounded-full blur-[30px] opacity-20 animate-pulse"></div>
               </div>
               <h3 className="text-3xl font-black text-foreground uppercase tracking-tight mb-4 leading-tight">Neural Simulation Matrix</h3>
               <p className="text-base font-medium text-muted-foreground max-w-sm mx-auto leading-relaxed uppercase tracking-tighter opacity-60">Select an environment instance from the strategy grid to begin deep-compute modeling and stress-path identification.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}

function BacktestTab({ result, loading, theme }) {
  if (loading) return <Loader />;
  if (!result || !result.proposed) return <EmptyState label="Backtest" />;

  const proposed = result.proposed?.summary || {};
  const current = result.current?.summary || {};
  const diffReturn = (proposed.total_return || 0) - (current.total_return || 0);
  const diffSharpe = (proposed.sharpe_ratio || 0) - (current.sharpe_ratio || 0);

  const proposedPrices = result.proposed?.path_metrics?.price_series || [];
  const currentPrices = result.current?.path_metrics?.price_series || [];

  const normalizeToReturns = (prices) => {
    if (!prices || prices.length < 2) return [];
    const base = prices[0] || 1;
    return prices.map((price, i) => ({
      day: i + 1,
      value: ((price / base) - 1) * 100,
    }));
  };

  const proposedReturns = normalizeToReturns(proposedPrices);
  const currentReturns = normalizeToReturns(currentPrices);

  const chartData = proposedReturns.map((item, i) => ({
    day: item.day,
    'Current Base': currentReturns[i]?.value ?? null,
    'Proposed Strategy': item.value,
  }));

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="bg-accent/20 border border-border/50 rounded-[2.5rem] p-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-6">
          <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] flex items-center">
            <TrendingUp size={16} className="mr-3 text-primary" /> Alpha Divergence Path
          </h4>
          <div className="flex items-center space-x-6">
             <div className="flex items-center">
               <div className="w-2.5 h-2.5 rounded-full bg-slate-400 mr-3 opacity-50"></div>
               <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Base Core</span>
             </div>
             <div className="flex items-center">
               <div className="w-2.5 h-2.5 rounded-full bg-bullish mr-3 shadow-[0_0_10px_hsl(var(--bullish)/0.5)]"></div>
               <span className="text-[10px] font-black text-bullish uppercase tracking-widest">Pivot Strategy</span>
             </div>
          </div>
        </div>
        
        <div className="h-[380px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke={theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'} vertical={false} />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} interval={Math.floor(chartData.length / 8)} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `${v > 0 ? '+' : ''}${v.toFixed(0)}%`} />
              <Tooltip content={<CustomTooltip />} />
              <Line type="monotone" dataKey="Current Base" stroke={COLORS.slate} strokeWidth={2} dot={false} strokeDasharray="5 5" opacity={0.3} animationDuration={1500} />
              <Line type="monotone" dataKey="Proposed Strategy" stroke={COLORS.bullish} strokeWidth={4} dot={false} animationDuration={1000} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <Card className="rounded-[2.5rem] p-10 border-none shadow-xl shadow-black/5 relative overflow-hidden group">
           <div className={cn("absolute -top-10 -right-10 p-4 opacity-[0.03] group-hover:rotate-12 transition-all duration-700", proposed.total_return >= 0 ? 'text-bullish' : 'text-destructive')}>
              <TrendingUp size={180} />
           </div>
           <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 block">Strategy Alpha Yield</span>
           <div className="flex items-center space-x-8">
              <span className={cn("text-6xl font-black tabular-nums tracking-tighter", proposed.total_return >= 0 ? 'text-bullish' : 'text-destructive')}>
                {proposed.total_return >= 0 ? '+' : ''}{proposed.total_return?.toFixed(1)}%
              </span>
              {diffReturn !== 0 && (
                <Badge variant={diffReturn > 0 ? "bullish" : "destructive"} className="px-4 py-1.5 rounded-xl font-black uppercase text-[10px] shadow-sm">
                   {diffReturn > 0 ? 'Surplus' : 'Deficit'}: {Math.abs(diffReturn).toFixed(1)}%
                </Badge>
              )}
           </div>
        </Card>

        <Card className="rounded-[2.5rem] p-10 border-none shadow-xl shadow-black/5 relative overflow-hidden group">
           <div className="absolute -top-10 -right-10 p-4 opacity-[0.03] text-primary group-hover:rotate-12 transition-all duration-700">
              <Shield size={180} />
           </div>
           <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 block">Risk Efficiency (Sharpe)</span>
           <div className="flex items-center space-x-8">
              <span className={cn("text-6xl font-black tabular-nums tracking-tighter", proposed.sharpe_ratio >= 1 ? 'text-primary' : 'text-amber-500')}>
                {proposed.sharpe_ratio?.toFixed(2)}
              </span>
              {diffSharpe !== 0 && (
                <Badge variant={diffSharpe > 0 ? "bullish" : "secondary"} className="px-4 py-1.5 rounded-xl font-black uppercase text-[10px] shadow-sm">
                   {diffSharpe > 0 ? 'Efficiency Boost' : 'Risk Spike'}
                </Badge>
              )}
           </div>
        </Card>
      </div>

      <Card className="rounded-[2.5rem] p-10 border-none bg-accent/20 border border-border/50">
        <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-10">Quantum Matrix Breakdown</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-10">
          {[
            { label: 'Volatility', val: `${proposed.volatility?.toFixed(2)}%`, color: 'text-foreground' },
            { label: 'Max Drawdown', val: `-${proposed.max_drawdown?.toFixed(2)}%`, color: 'text-destructive' },
            { label: 'Peak Velocity', val: `+${proposed.best_day?.toFixed(2)}%`, color: 'text-bullish' },
            { label: 'Valley Low', val: `${proposed.worst_day?.toFixed(2)}%`, color: 'text-destructive' }
          ].map((m, i) => (
            <div key={i} className="space-y-2">
              <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest opacity-60 block">{m.label}</span>
              <p className={cn("text-2xl font-black tabular-nums tracking-tight", m.color)}>{m.val}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function MonteCarloTab({ result, loading, horizon, theme }) {
  if (loading) return <Loader color="text-purple-500" />;
  if (!result || !result.proposed) return <EmptyState label="Monte Carlo" />;

  const mc = result.proposed || {};
  const stats = mc.statistics || {};
  const cone = mc.cone_of_uncertainty || {};

  const coneData = cone.days?.map((day, i) => ({
    day,
    'p95': cone.p95?.[i] || 0,
    'p75': cone.p75?.[i] || 0,
    'Target': cone.p50?.[i] || 0,
    'p25': cone.p25?.[i] || 0,
    'p05': cone.p5?.[i] || 0,
  })) || [];

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="bg-purple-500/5 border border-purple-500/20 rounded-[2.5rem] p-10">
        <h4 className="text-[10px] font-black text-purple-500 uppercase tracking-[0.2em] mb-10 flex items-center">
          <Target size={16} className="mr-3" /> Probabilistic Confidence Cone ({horizon}D)
        </h4>
        
        <div className="h-[380px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={coneData}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(139, 92, 246, 0.05)" vertical={false} />
              <XAxis dataKey="day" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} interval={Math.floor(coneData.length / 5)} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
              <Tooltip content={<CustomTooltip />} />
              <Area type="monotone" dataKey="p95" stroke={COLORS.bullish} fill={COLORS.bullish} fillOpacity={0.05} strokeWidth={1} name="Max Potential" />
              <Area type="monotone" dataKey="p75" stroke={COLORS.cyan} fill={COLORS.cyan} fillOpacity={0.05} strokeWidth={1} name="Optimistic" />
              <Area type="monotone" dataKey="Target" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.15} strokeWidth={4} name="Neural Mean" />
              <Area type="monotone" dataKey="p25" stroke={COLORS.gold} fill={COLORS.gold} fillOpacity={0.05} strokeWidth={1} name="Cautious" />
              <Area type="monotone" dataKey="p05" stroke={COLORS.bearish} fill={COLORS.bearish} fillOpacity={0.1} strokeWidth={1} name="Extreme Risk" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
        {[
          { label: 'Forecasted Mean', val: `₹${Math.round(stats.mean_final || 0).toLocaleString()}`, sub: `${(stats.mean_return || 0).toFixed(1)}% Projected`, color: 'text-purple-500' },
          { label: 'Alpha Target (P95)', val: `₹${Math.round(mc.percentiles_value?.p95 || 0).toLocaleString()}`, sub: 'Ceiling Vector', color: 'text-bullish' },
          { label: 'Safety Floor (P05)', val: `₹${Math.round(mc.percentiles_value?.p05 || 0).toLocaleString()}`, sub: 'Extreme Correction', color: 'text-destructive' },
          { label: 'Success Index', val: `${Math.round(mc.probabilities?.above_initial || 0)}%`, sub: 'P(Alpha) > 0', color: 'text-cyan-500' }
        ].map((item, i) => (
          <Card key={i} className="rounded-3xl p-8 text-center border-none shadow-xl shadow-black/5 bg-accent/20">
            <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block mb-3 opacity-60">{item.label}</span>
            <p className={cn("text-2xl font-black tabular-nums tracking-tight", item.color)}>{item.val}</p>
            <p className="text-[10px] font-bold text-muted-foreground mt-2 uppercase tracking-tighter opacity-50">{item.sub}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

function StressTestTab({ result, loading, scenario, setScenario, onScenarioChange, theme }) {
  const scenarios = [
    { id: '2008_CRISIS', name: 'Recession Matrix (2008)' },
    { id: 'COVID_2020', name: 'Pandemic Shock (2020)' },
    { id: 'DOTCOM_2000', name: 'Tech De-rating (2000)' },
    { id: 'RATE_HIKE', name: 'Aggressive Monetary Hike' },
    { id: 'INFLATION_2022', name: 'Macro Inflationary Event' },
  ];

  if (loading) return <Loader color="text-amber-500" />;
  if (!result || !result.portfolio_summary) return <EmptyState label="Stress Matrix" />;

  const summary = result.portfolio_summary || {};
  const holdings = result.holdings_impact || [];
  const lossPct = Math.abs(summary.total_loss_pct || 0);

  const chartData = [
    { name: 'Equilibrium', value: summary.total_base_value || 0, color: COLORS.bullish },
    { name: 'Stressed Value', value: summary.total_stressed_value || 0, color: COLORS.bearish },
  ];

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="bg-amber-500/5 border border-amber-500/20 rounded-[2.5rem] p-10">
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-10 gap-8">
          <h4 className="text-[10px] font-black text-amber-500 uppercase tracking-[0.2em] flex items-center">
            <AlertTriangle size={16} className="mr-3" /> Impact Vector: {scenarios.find(s => s.id === scenario)?.name}
          </h4>
          <div className="flex items-center space-x-4 bg-background/50 border border-border/50 rounded-2xl p-2.5 shadow-inner">
             <select
                value={scenario}
                onChange={e => setScenario(e.target.value)}
                className="bg-transparent text-[10px] font-black text-foreground outline-none cursor-pointer px-3 uppercase tracking-widest"
              >
                {scenarios.map(s => (
                  <option key={s.id} value={s.id}>{s.name}</option>
                ))}
              </select>
              <Button
                onClick={onScenarioChange}
                size="sm"
                className="rounded-xl font-black text-[9px] uppercase tracking-widest px-5 shadow-lg shadow-primary/20"
              >
                Re-Simulate
              </Button>
          </div>
        </div>
        
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 40, right: 40 }}>
              <XAxis type="number" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} tickFormatter={v => `₹${(v/1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={10} tickLine={false} axisLine={false} width={100} />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'hsl(var(--accent))', opacity: 0.2 }} />
              <Bar dataKey="value" radius={[0, 12, 12, 0]} barSize={45}>
                {chartData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
        <Card className="rounded-3xl p-10 bg-accent/20 border-none flex flex-col justify-center">
           <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-60">Maximum Capital Drawdown</span>
           <p className="text-4xl font-black text-destructive tabular-nums tracking-tighter">₹{summary.total_loss?.toLocaleString()}</p>
           <Badge variant="destructive" className="mt-4 self-start font-black text-[10px] px-3 py-1 rounded-lg">-{lossPct.toFixed(2)}% Impact</Badge>
        </Card>
        
        <Card className="rounded-3xl p-10 bg-accent/20 border-none flex flex-col justify-center">
           <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-4 opacity-60">Recovery Factor</span>
           <p className="text-4xl font-black text-primary tabular-nums tracking-tighter">~{summary.recovery_days || 120}D</p>
           <p className="text-[10px] font-bold text-muted-foreground mt-4 uppercase tracking-tighter opacity-50 italic">Est. Days to Equilibrium</p>
        </Card>

        <Card className={cn("rounded-3xl p-10 border-none flex items-center space-x-6", lossPct > 25 ? 'bg-destructive/5' : 'bg-bullish/5')}>
           <div className={cn("w-16 h-16 rounded-[2rem] flex items-center justify-center text-white shadow-xl flex-shrink-0", lossPct > 25 ? 'bg-destructive shadow-destructive/20' : 'bg-bullish shadow-bullish/20')}>
              <Shield size={32} />
           </div>
           <div>
              <p className={cn("text-xl font-black uppercase tracking-tight leading-none mb-2", lossPct > 25 ? 'text-destructive' : 'text-bullish')}>
                {lossPct > 25 ? 'Resilience Gap' : 'Integrity High'}
              </p>
              <p className="text-[10px] font-bold text-muted-foreground leading-relaxed uppercase tracking-tighter opacity-70">
                {lossPct > 25 ? 'Critical structural vulnerability detected in current matrix.' : 'Strategy shows robust defensive posture across shock models.'}
              </p>
           </div>
        </Card>
      </div>
      
      {holdings.length > 0 && (
        <Card className="rounded-[2.5rem] p-10 border-none bg-accent/10">
           <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-10 flex items-center">
             <Activity size={14} className="mr-3" /> Asset Vulnerability Index
           </h4>
           <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-10">
              {holdings.slice(0, 12).map((h, i) => (
                <div key={i} className="text-center group">
                  <div className="w-14 h-14 rounded-2xl bg-background border border-border flex items-center justify-center mx-auto mb-4 font-black text-xs text-foreground uppercase shadow-sm group-hover:border-destructive/30 transition-all">
                    {h.ticker.slice(0, 2)}
                  </div>
                  <span className="text-[10px] font-black text-foreground uppercase block leading-none tracking-widest">{h.ticker}</span>
                  <span className="text-xs font-black text-destructive mt-2 block tabular-nums">-{h.percentage_loss?.toFixed(1)}%</span>
                </div>
              ))}
           </div>
        </Card>
      )}
    </div>
  );
}

function RiskAnalysisTab({ analysis, loading, theme }) {
  if (loading) return <Loader color="text-cyan-500" />;
  if (!analysis || !analysis.risk_analysis) return <EmptyState label="Guardrail" />;

  const risk = analysis.risk_analysis || {};
  const regime = analysis.market_regime || {};
  const score = risk.overall_score || 0;
  const components = risk.components || {};

  return (
    <div className="space-y-12 animate-in fade-in slide-in-from-bottom-2 duration-500">
       <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <Card className="rounded-[2.5rem] p-10 bg-accent/20 border-none flex flex-col items-center justify-center">
             <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-10 opacity-60">Aggregate Risk Coefficient</span>
             <div className="relative w-56 h-56">
                <svg className="w-full h-full transform -rotate-90">
                  <circle cx="112" cy="112" r="95" stroke={theme === 'dark' ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.05)'} strokeWidth="14" fill="none" />
                  <circle 
                    cx="112" cy="112" r="95" 
                    stroke={score > 60 ? COLORS.bearish : score > 40 ? COLORS.gold : COLORS.brand}
                    strokeWidth="14" 
                    fill="none"
                    strokeDasharray={`${score * (2 * Math.PI * 95) / 100} 596.9`}
                    strokeLinecap="round"
                    className="transition-all duration-1500 ease-out"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-6xl font-black text-foreground tabular-nums tracking-tighter">{score}</span>
                  <Badge variant={score > 60 ? "destructive" : score > 40 ? "secondary" : "bullish"} className="mt-3 px-3 py-1 font-black text-[9px] uppercase tracking-widest">
                    {risk.risk_level} PROFILE
                  </Badge>
                </div>
             </div>
          </Card>

          <Card className="rounded-[2.5rem] p-10 bg-primary border-none text-primary-foreground relative overflow-hidden group">
             <div className="absolute -bottom-10 -right-10 p-4 opacity-10 group-hover:scale-110 transition-transform duration-700">
                <Globe size={220} />
             </div>
             <div className="relative z-10">
               <div className="flex items-center space-x-4 mb-10">
                  <div className="w-14 h-14 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center text-white border border-white/20 shadow-lg">
                    <Globe size={28} />
                  </div>
                  <div>
                     <span className="text-[10px] font-black uppercase tracking-[0.2em] opacity-70 leading-none block mb-1">Regime Detection</span>
                     <h3 className="text-2xl font-black uppercase tracking-tight">{regime.regime} {regime.emoji}</h3>
                  </div>
               </div>
               <p className="text-lg font-bold leading-relaxed mb-10 italic opacity-90 max-w-sm">"{regime.description}"</p>
               <div className="grid grid-cols-2 gap-6">
                  <div className="p-5 bg-white/10 backdrop-blur-md border border-white/10 rounded-2xl shadow-inner">
                     <span className="text-[10px] font-black uppercase block mb-2 opacity-60 tracking-widest">Vol Coefficient</span>
                     <span className="text-base font-black tabular-nums">{regime.metrics?.volatility}% INDEX</span>
                  </div>
                  <div className="p-5 bg-white/10 backdrop-blur-md border border-white/10 rounded-2xl shadow-inner">
                     <span className="text-[10px] font-black uppercase block mb-2 opacity-60 tracking-widest">Yield Momentum</span>
                     <span className="text-base font-black tabular-nums">{regime.metrics?.recent_return}% DELTA</span>
                  </div>
               </div>
             </div>
          </Card>
       </div>

       <Card className="rounded-[2.5rem] p-10 border-none shadow-xl shadow-black/5">
          <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-12">Core Probability Components</h4>
          <div className="space-y-10">
            {Object.entries(components).map(([key, value]) => (
              <div key={key}>
                <div className="flex justify-between items-end mb-3">
                  <span className="text-xs font-black text-foreground uppercase tracking-widest opacity-80">{key.replace('_', ' ')}</span>
                  <span className="text-xs font-black text-muted-foreground tabular-nums opacity-60">{value}/100</span>
                </div>
                <div className="h-3 bg-accent rounded-full overflow-hidden border border-border/20 relative p-0.5">
                  <div 
                    className={cn("h-full transition-all duration-1000 ease-out rounded-full", {
                      'bg-bullish shadow-[0_0_8px_hsl(var(--bullish)/0.3)]': value < 40,
                      'bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.3)]': value >= 40 && value <= 60,
                      'bg-destructive shadow-[0_0_8px_hsl(var(--destructive)/0.3)]': value > 60
                    })}
                    style={{ width: `${value}%` }}
                  />
                  {value > 80 && <div className="absolute inset-0 bg-destructive/10 animate-pulse rounded-full"></div>}
                </div>
              </div>
            ))}
          </div>
       </Card>

       {risk.recommendations && (
         <Card className="rounded-[3rem] p-10 bg-accent/20 border-none relative overflow-hidden group">
            <div className="absolute right-0 bottom-0 p-10 opacity-[0.02] transform group-hover:scale-110 transition-transform duration-700">
               <Cpu size={250} />
            </div>
            <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-10 opacity-60">Strategic Alignment Mandates</h4>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 relative z-10">
               {risk.recommendations.map((rec, i) => (
                 <div key={i} className="flex items-start space-x-4 bg-background/50 border border-border/50 p-6 rounded-3xl group/item hover:border-primary/30 transition-all">
                    <div className="p-2 bg-primary/10 rounded-xl text-primary mt-0.5">
                      <Zap size={18} className="fill-current" />
                    </div>
                    <p className="text-sm font-bold leading-relaxed text-foreground opacity-80 group-hover/item:opacity-100 transition-opacity">{rec}</p>
                 </div>
               ))}
            </div>
         </Card>
       )}
    </div>
  );
}

function Loader({ color = "text-primary" }) {
  return (
    <div className="flex h-80 items-center justify-center flex-col space-y-6">
      <div className={cn("animate-spin rounded-full h-12 w-12 border-b-2", color)}></div>
      <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.25em] animate-pulse">Synchronizing Neural Paths...</span>
    </div>
  );
}

function EmptyState({ label }) {
  return (
    <div className="py-24 text-center flex flex-col items-center">
       <div className="w-20 h-20 bg-accent/50 rounded-[40px] flex items-center justify-center mb-8 border border-border shadow-inner">
         <Play size={32} className="text-muted-foreground opacity-20" />
       </div>
       <h4 className="text-2xl font-black text-foreground uppercase tracking-tight mb-3">{label} Instance Pending</h4>
       <p className="text-xs font-bold text-muted-foreground max-w-xs mx-auto uppercase tracking-widest opacity-60 leading-relaxed">Initiate "Launch Matrix" to populate the probabilistic computation grid.</p>
    </div>
  );
}
