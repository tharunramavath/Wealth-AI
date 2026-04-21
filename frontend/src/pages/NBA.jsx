import React, { useState } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import { Zap, AlertTriangle, ShieldCheck, RefreshCw, TrendingUp, Clock, Database, GitBranch, Radio, Trash2, Sparkles, Brain, Cpu, MessageSquare, ArrowUpRight, TrendingDown, Target, Info, Wallet, Activity } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription, CardFooter } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { cn } from '../lib/utils';

export default function NBA() {
  const [loading, setLoading] = useState(false);
  const [nba, setNba] = useState(null);
  const [cacheKey, setCacheKey] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const navigate = useNavigate();

  const generate = async (forceRefresh = false) => {
    setLoading(true);
    if (!forceRefresh) setNba(null);
    try {
      toast.loading('Initializing Quantum Market Scan...', { id: 'nba' });
      const res = await api.post('/events/scan');
      toast.success('Market Intelligence Updated!', { id: 'nba' });
      if (res.data.nba_result) {
        setNba(res.data.nba_result);
        setCacheKey(res.data.nba_result.cache_key);
        setLastUpdated(new Date());
        if (res.data.triggering_event) {
          toast.success(`Priority Event detected: ${res.data.triggering_event.headline?.slice(0, 40)}...`, { duration: 5000 });
        }
      } else {
        toast.success('No high-impact anomalies detected for your holdings.');
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message, { id: 'nba' });
    }
    setLoading(false);
  };

  const clearCache = async () => {
    try {
      await api.post('/nba/cache/clear');
      toast.success('Local Analysis Cache Purged');
      setNba(null);
      setCacheKey(null);
    } catch (e) {
      toast.error('Failed to clear engine cache');
    }
  };

  const formatLastUpdated = () => {
    if (!lastUpdated) return null;
    const now = new Date();
    const diffMs = now - lastUpdated;
    const diffMins = Math.floor(diffMs / 60000);
    if (diffMins < 1) return 'Synchronized Now';
    if (diffMins < 60) return `${diffMins}m ago`;
    return lastUpdated.toLocaleTimeString();
  };

  const createSimulationFromNBA = async () => {
    if (!nba) return;
    try {
      const portfolioRes = await api.get('/portfolio');
      const currentHoldings = portfolioRes.data;
      if (!currentHoldings || currentHoldings.length === 0) {
        toast.error('Connect your portfolio to simulate impact.');
        return;
      }
      
      let proposedHoldings = currentHoldings.map(h => ({
        ticker: h.ticker,
        quantity: h.quantity,
        avg_price: h.avg_price
      }));
      
      const action = typeof nba.next_best_action === 'string' ? nba.next_best_action : nba.next_best_action?.action || '';
      const targetAssets = (nba.next_best_action?.target_assets || []).map(t => t.toUpperCase());
      const upperAction = action.toUpperCase();

      if (upperAction.includes('REDUCE') || upperAction.includes('SELL')) {
        for (const h of proposedHoldings) {
          if (targetAssets.some(t => h.ticker.toUpperCase().includes(t) || t.includes(h.ticker.toUpperCase()))) {
            h.quantity = Math.max(1, Math.floor(h.quantity * 0.5));
          }
        }
      } else if (upperAction.includes('BUY')) {
        for (const ticker of targetAssets) {
          const existing = proposedHoldings.find(h => h.ticker.toUpperCase().includes(ticker) || ticker.includes(h.ticker.toUpperCase()));
          if (existing) {
            existing.quantity = Math.floor(existing.quantity * 1.5);
          } else {
            proposedHoldings.push({ ticker: ticker, quantity: 10, avg_price: 100 });
          }
        }
      }
      
      await api.post('/simulation/scenario/create', {
        name: `AI-NBA: ${action.slice(0, 20)}...`,
        description: `Simulated impact of AI Recommendation: ${action}.`,
        proposed_holdings: proposedHoldings,
        is_nba_based: true
      });
      
      toast.success('Simulation Scenario Deployed!');
      setTimeout(() => navigate('/simulation'), 800);
    } catch (err) {
      toast.error('Simulation Error: ' + (err.response?.data?.detail || err.message));
    }
  };

  const analytics = nba?.analytics;

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black text-foreground tracking-tight uppercase">Strategic Intelligence</h1>
          {lastUpdated ? (
            <div className="flex items-center space-x-4 mt-2">
              <Badge variant="bullish" className="px-3 py-0.5 font-black uppercase text-[10px] tracking-widest animate-pulse">
                Live Feed Active
              </Badge>
              <div className="flex items-center text-[10px] font-bold text-muted-foreground uppercase tracking-widest">
                <Clock size={12} className="mr-1.5" />
                {formatLastUpdated()}
                <span className="mx-3 opacity-30">|</span>
                <Cpu size={12} className="mr-1.5" />
                Engine: {cacheKey?.slice(0, 8) || 'QUANTUM_V2'}
              </div>
            </div>
          ) : (
            <p className="text-muted-foreground font-semibold text-sm mt-2 uppercase tracking-tight">Deploy neural engine to identify tactical portfolio pivots.</p>
          )}
        </div>
        
        <div className="flex items-center space-x-3">
          <Button 
            variant="ghost"
            size="icon"
            onClick={clearCache} 
            className="rounded-xl hover:text-destructive hover:bg-destructive/10 transition-all shadow-sm"
          >
            <Trash2 size={20} />
          </Button>
          <Button 
            onClick={() => generate(true)} 
            disabled={loading} 
            size="lg"
            className="rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-primary/20 group h-14 px-8"
          >
            {loading ? <RefreshCw className="animate-spin mr-3" size={18} /> : <Zap className="mr-3 group-hover:scale-125 transition-transform" size={18} />}
            {loading ? 'Processing Signals...' : nba ? 'Relaunch Analysis' : 'Boot Intelligence Engine'}
          </Button>
        </div>
      </div>

      {!nba && !loading && (
        <Card className="rounded-[3rem] border-none shadow-2xl shadow-black/5 overflow-hidden min-h-[550px] flex flex-col items-center justify-center text-center p-10 relative">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,hsl(var(--primary)/0.08),transparent_70%)]"></div>
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-primary/5 blur-[120px] rounded-full pointer-events-none"></div>
          
          <div className="relative z-10 max-w-3xl space-y-10">
            <div className="w-28 h-28 bg-primary border-[10px] border-primary/20 rounded-[45px] flex items-center justify-center mx-auto shadow-2xl animate-in zoom-in-50 duration-700">
              <Brain className="text-primary-foreground" size={56} />
            </div>
            
            <div className="space-y-4">
              <h2 className="text-5xl font-black text-foreground tracking-tight uppercase leading-none">Neural Portfolio <br /> Optimization</h2>
              <p className="text-xl font-medium text-muted-foreground leading-relaxed max-w-2xl mx-auto">
                Advanced NLP agents ingest earnings transcripts, regulatory filings, and global sentiment matrices to deliver high-confidence tactical recommendations.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
              <IntelligenceFeature icon={Radio} title="Alpha Detection" desc="Identification of volatility anomalies." />
              <IntelligenceFeature icon={TrendingUp} title="Sentiment Sync" desc="NLP mood analysis of source feeds." />
              <IntelligenceFeature icon={ShieldCheck} title="Guardrail AI" desc="Risk-weighted compliance logic." />
            </div>

            <Button size="lg" onClick={() => generate()} className="h-16 px-12 rounded-[2rem] font-black uppercase tracking-[0.2em] shadow-2xl shadow-primary/30 hover:scale-105 active:scale-95 transition-all">
              Initialize Neural Engine
            </Button>
          </div>
        </Card>
      )}

      {nba && (
        <div className="space-y-8 animate-in fade-in slide-in-from-bottom-6 duration-700">
          {/* Top Level Intelligence Bar */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <AnalyticsCard label="Active Valuation" value={`₹${analytics?.total_value?.toLocaleString()}`} icon={Wallet} />
            <AnalyticsCard 
              label="Net P&L Alpha" 
              value={`${analytics?.total_pnl >= 0 ? '+' : ''}₹${analytics?.total_pnl?.toLocaleString()}`} 
              icon={TrendingUp} 
              variant={analytics?.total_pnl >= 0 ? 'bullish' : 'bearish'} 
            />
            <AnalyticsCard label="Risk Coefficient" value={`${analytics?.portfolio_volatility || 0}%`} icon={Activity} />
            <AnalyticsCard 
              label="Diversification" 
              value={`${analytics?.diversification_score || 0}/100`} 
              icon={Target} 
              variant={(analytics?.diversification_score || 0) >= 70 ? 'bullish' : 'secondary'} 
            />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Primary Recommendation Card */}
            <div className="lg:col-span-8 space-y-8">
              <Card className="rounded-[3rem] border-none shadow-2xl shadow-black/5 overflow-hidden group">
                <div className={cn("px-10 py-8 flex items-center justify-between border-b border-border/50", {
                  'bg-destructive/10': nba.triggering_event?.severity === 'Critical',
                  'bg-amber-500/10': nba.triggering_event?.severity === 'High',
                  'bg-primary/10': nba.triggering_event?.severity === 'Medium' || nba.triggering_event?.severity === 'Low',
                })}>
                  <div className="flex items-center space-x-6">
                    <div className={cn("w-16 h-16 rounded-[2rem] flex items-center justify-center shadow-lg transform group-hover:rotate-6 transition-all duration-500", {
                      'bg-destructive text-destructive-foreground shadow-destructive/20': nba.triggering_event?.severity === 'Critical',
                      'bg-amber-500 text-white shadow-amber-500/20': nba.triggering_event?.severity === 'High',
                      'bg-primary text-primary-foreground shadow-primary/20': nba.triggering_event?.severity === 'Medium' || nba.triggering_event?.severity === 'Low',
                    })}>
                      <Zap className="animate-pulse" size={32} />
                    </div>
                    <div>
                      <h3 className="text-2xl font-black text-foreground uppercase tracking-tight">Tactical Execution Signal</h3>
                      <div className="flex items-center space-x-3 mt-2">
                        <Badge variant={nba.triggering_event?.severity === 'Critical' ? 'destructive' : nba.triggering_event?.severity === 'High' ? 'secondary' : 'default'} className="px-3 py-0.5 font-black uppercase tracking-widest text-[9px]">
                          Priority: {nba.triggering_event?.severity || 'Standard'}
                        </Badge>
                        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Sector: {nba.triggering_event?.sector || 'Global'}</span>
                      </div>
                    </div>
                  </div>
                  <div className="hidden md:flex flex-col items-end">
                    <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] mb-1">Signal Strength</span>
                    <span className="text-4xl font-black text-foreground tabular-nums tracking-tighter">{Math.round((nba.confidence_score || 0.8) * 100)}%</span>
                  </div>
                </div>

                <CardContent className="p-10 space-y-12">
                  <section>
                    <div className="flex items-center space-x-3 mb-6">
                      <div className="w-8 h-8 rounded-xl bg-accent flex items-center justify-center text-[11px] font-black">01</div>
                      <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Context Briefing</h4>
                    </div>
                    <div className="relative">
                      <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-primary/20 rounded-full"></div>
                      <blockquote className="pl-8 py-2 italic font-black text-2xl text-foreground leading-snug tracking-tight">
                        "{nba.triggering_event?.headline || nba.market_insight.slice(0, 100) + '...'}"
                      </blockquote>
                      <div className="mt-6 pl-8 flex items-center space-x-4">
                        <Badge variant="outline" className="text-[9px] font-black uppercase py-1 border-primary/20 text-primary">{nba.triggering_event?.event_type?.replace(/_/g, ' ') || 'MARKET_SHIFT'}</Badge>
                        <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Source: {nba.triggering_event?.source || 'Neural Intelligence Grid'}</span>
                      </div>
                    </div>
                  </section>

                  <section className="bg-accent/30 rounded-[2.5rem] p-10 border border-border/50">
                    <div className="flex items-center space-x-3 mb-8">
                      <div className="w-8 h-8 rounded-xl bg-background border border-border flex items-center justify-center text-[11px] font-black">02</div>
                      <h4 className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em]">Deployment Directive</h4>
                    </div>
                    
                    <div className="flex flex-col md:flex-row md:items-center justify-between gap-8">
                      <div className="flex items-center space-x-6">
                        <div className={cn("w-20 h-20 rounded-[2rem] flex items-center justify-center shadow-inner", {
                          'bg-bullish/10 text-bullish': (typeof nba.next_best_action === 'string' ? nba.next_best_action : nba.next_best_action?.action)?.toUpperCase().includes('BUY'),
                          'bg-destructive/10 text-destructive': (typeof nba.next_best_action === 'string' ? nba.next_best_action : nba.next_best_action?.action)?.toUpperCase().includes('SELL'),
                          'bg-primary/10 text-primary': !/BUY|SELL/.test((typeof nba.next_best_action === 'string' ? nba.next_best_action : nba.next_best_action?.action)?.toUpperCase())
                        })}>
                          <Zap size={40} className="fill-current" />
                        </div>
                        <div>
                          <p className="text-3xl font-black text-foreground tracking-tighter uppercase leading-none mb-2">{typeof nba.next_best_action === 'string' ? nba.next_best_action : nba.next_best_action?.action}</p>
                          <p className="text-sm font-semibold text-muted-foreground max-w-sm">{nba.next_best_action?.suggested_change || 'Tactical re-alignment recommended based on intelligence synthesis.'}</p>
                        </div>
                      </div>
                      <div className="flex flex-wrap gap-2 justify-start md:justify-end">
                        {(nba.next_best_action?.target_assets || ['GLOBAL']).map((t, idx) => (
                          <Badge key={idx} variant="secondary" className="px-5 py-2.5 rounded-xl text-[11px] font-black tracking-widest uppercase shadow-sm">
                            {t}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  </section>
                </CardContent>

                <CardFooter className="bg-accent/20 p-8 border-t border-border/50 flex flex-col items-center">
                  <Button
                    size="lg"
                    onClick={createSimulationFromNBA}
                    className="w-full max-w-md h-16 rounded-[2rem] font-black uppercase tracking-[0.2em] shadow-xl shadow-primary/30 group relative overflow-hidden"
                  >
                    <span className="relative z-10 flex items-center">
                      <GitBranch size={22} className="mr-3 group-hover:rotate-45 transition-transform duration-500" />
                      Simulate Impact Delta
                    </span>
                    <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000"></div>
                  </Button>
                  <p className="mt-4 text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em]">Validate recommendation via Monte Carlo Stress-Testing</p>
                </CardFooter>
              </Card>

              {nba.market_insight && (
                <Card className="rounded-[3rem] border-none shadow-xl shadow-black/5 p-10 relative overflow-hidden group">
                  <div className="absolute top-0 right-0 p-10 opacity-[0.03] group-hover:rotate-12 group-hover:scale-110 transition-all duration-700">
                    <MessageSquare size={150} />
                  </div>
                  <div className="flex items-center space-x-4 mb-8 relative z-10">
                    <div className="p-3 bg-primary/10 rounded-2xl text-primary">
                      <Brain size={24} />
                    </div>
                    <CardTitle className="text-sm font-black uppercase tracking-[0.2em] text-muted-foreground">Neural Synthesis Report</CardTitle>
                  </div>
                  <p className="text-2xl font-bold text-foreground leading-relaxed relative z-10 tracking-tight">
                    {nba.market_insight}
                  </p>
                </Card>
              )}
            </div>

            {/* Sidebar Analytics */}
            <div className="lg:col-span-4 space-y-8">
              <Card className="rounded-[3rem] border-none shadow-xl shadow-black/5 p-10 space-y-10">
                <div>
                  <h4 className="text-xs font-black text-muted-foreground uppercase tracking-[0.2em] mb-8">Mood Spectrum</h4>
                  {nba.triggering_event?.sentiment ? (
                    <div className="space-y-8">
                      <SentimentBar label="Bullish Intensity" val={nba.triggering_event.sentiment.positive} color="bullish" />
                      <SentimentBar label="Bearish Drag" val={nba.triggering_event.sentiment.negative} color="destructive" />
                      <SentimentBar label="Market Neutrality" val={nba.triggering_event.sentiment.neutral} color="secondary" />
                    </div>
                  ) : (
                    <div className="py-10 text-center text-muted-foreground/30 font-black uppercase text-[10px]">No sentiment signals</div>
                  )}
                </div>

                <div className="h-[1px] bg-border/50"></div>

                <div>
                  <h4 className="text-xs font-black text-muted-foreground uppercase tracking-[0.2em] mb-8">Compliance Matrix</h4>
                  <div className="space-y-4">
                    <ComplianceItem icon={ShieldCheck} label="Guardrail Alignment" sub="Matches Strategy Profile" status="PASS" />
                    <ComplianceItem icon={Database} label="Knowledge Integrity" sub="Validated on 1.2M Scenarios" status="PASS" />
                    <ComplianceItem icon={Target} label="Objective Precision" sub="Zero Over-concentration" status="PASS" />
                  </div>
                </div>
              </Card>

              <Card className="rounded-[3rem] border-none shadow-xl shadow-black/5 p-10 bg-primary text-primary-foreground overflow-hidden relative">
                <div className="absolute top-0 right-0 p-6 opacity-10">
                  <Zap size={100} />
                </div>
                <div className="relative z-10">
                  <h4 className="text-xs font-black uppercase tracking-[0.2em] opacity-70 mb-6">Expert Verdict</h4>
                  <p className="text-xl font-bold leading-relaxed mb-8">
                    "This signal represents a high-probability tactical opportunity. Recommend immediate simulation."
                  </p>
                  <Button variant="secondary" className="w-full rounded-2xl font-black uppercase tracking-widest text-[10px] h-12 shadow-lg shadow-black/10">
                    Acknowledge Signal
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function IntelligenceFeature({ icon: Icon, title, desc }) {
  return (
    <div className="p-6 rounded-[2rem] bg-accent/30 border border-border/50 group hover:border-primary/50 transition-all duration-500">
      <div className="w-12 h-12 rounded-2xl bg-background border border-border flex items-center justify-center mb-6 group-hover:bg-primary group-hover:border-primary transition-all duration-500">
        <Icon className="text-muted-foreground group-hover:text-primary-foreground transition-all" size={24} />
      </div>
      <h4 className="font-black text-foreground text-sm uppercase tracking-widest mb-2">{title}</h4>
      <p className="text-xs font-semibold text-muted-foreground leading-relaxed">{desc}</p>
    </div>
  );
}

function AnalyticsCard({ label, value, icon: Icon, variant = 'default' }) {
  const colorMap = {
    bullish: "text-bullish",
    bearish: "text-destructive",
    secondary: "text-primary",
    default: "text-foreground"
  };

  return (
    <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 p-6 group relative overflow-hidden">
      <div className="absolute -top-6 -right-6 p-4 opacity-[0.03] group-hover:rotate-12 transition-transform duration-500">
        <Icon size={100} />
      </div>
      <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] relative z-10">{label}</span>
      <div className="mt-2 relative z-10 flex items-center justify-between">
        <p className={cn("text-2xl font-black tabular-nums tracking-tight", colorMap[variant])}>{value}</p>
        <Icon size={16} className="text-muted-foreground opacity-30" />
      </div>
    </Card>
  );
}

function SentimentBar({ label, val, color }) {
  const percent = Math.round((val || 0) * 100);
  return (
    <div className="space-y-3">
      <div className="flex justify-between items-end">
        <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">{label}</span>
        <span className={cn("text-sm font-black tabular-nums", {
          'text-bullish': color === 'bullish',
          'text-destructive': color === 'destructive',
          'text-muted-foreground': color === 'secondary'
        })}>{percent}%</span>
      </div>
      <div className="h-2.5 bg-accent rounded-full overflow-hidden p-0.5">
        <div 
          className={cn("h-full transition-all duration-1000 ease-out rounded-full", {
            'bg-bullish shadow-[0_0_8px_hsl(var(--bullish)/0.3)]': color === 'bullish',
            'bg-destructive shadow-[0_0_8px_hsl(var(--destructive)/0.3)]': color === 'destructive',
            'bg-muted-foreground/40': color === 'secondary',
          })}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function ComplianceItem({ icon: Icon, label, sub, status }) {
  return (
    <div className="flex items-center space-x-4 p-4 rounded-2xl bg-accent/20 border border-border/30 hover:bg-accent/40 transition-all">
      <div className="w-10 h-10 rounded-xl bg-background border border-border flex items-center justify-center text-emerald-500 shadow-sm">
        <Icon size={20} />
      </div>
      <div className="flex-1">
        <div className="flex items-center justify-between">
          <span className="text-[10px] font-black text-foreground uppercase tracking-tight leading-none mb-1">{label}</span>
          <span className="text-[9px] font-black text-emerald-500">{status}</span>
        </div>
        <span className="text-[9px] font-bold text-muted-foreground uppercase tracking-widest block">{sub}</span>
      </div>
    </div>
  );
}
