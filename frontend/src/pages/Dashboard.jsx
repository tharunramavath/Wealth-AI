import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis } from 'recharts';
import { Activity, Shield, ArrowUpRight, Sparkles, TrendingUp, TrendingDown, AlertTriangle, Search, Wallet, BarChart3, PieChart as PieChartIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import CorrelationMatrix from '../components/CorrelationMatrix';
import PortfolioForecastSummary from '../components/PortfolioForecastSummary';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { useTheme } from '../hooks/use-theme';
import { cn } from '../lib/utils';

export default function Dashboard() {
  const [data, setData] = useState({ portfolio: [], analytics: null, riskProfile: null, loading: true });
  const navigate = useNavigate();
  const { theme } = useTheme();
  const userName = localStorage.getItem('user_name') || 'Investor';
  const [showWelcome, setShowWelcome] = useState(() => {
    return localStorage.getItem('show_welcome') === 'true';
  });

  const fetchData = () => {
    setData(prev => ({ ...prev, loading: true }));
    Promise.all([
      api.get('/portfolio'),
      api.get('/portfolio/analytics'),
      api.get('/onboarding/risk-profile')
    ]).then(([p, a, r]) => {
      let analytics = a.data;
      if (analytics && analytics.error) {
        analytics = {
          total_value: 0,
          total_invested: 0,
          total_pnl: 0,
          total_pnl_pct: 0,
          sector_allocation: {},
          top_holdings: [],
          best_performer: null,
          worst_performer: null,
          volatility: 0,
          sharpe_ratio: 0,
          max_drawdown: 0,
          diversification_score: 0,
        };
      }
      setData({ portfolio: p.data, analytics, riskProfile: r.data, loading: false });
    }).catch(() => {
      setData({ portfolio: [], analytics: null, riskProfile: null, loading: false });
    });
  };

  useEffect(() => {
    fetchData();
    const handleFocus = () => fetchData();
    window.addEventListener('focus', handleFocus);
    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  useEffect(() => {
    if (showWelcome) {
      const timer = setTimeout(() => {
        setShowWelcome(false);
        localStorage.setItem('show_welcome', 'false');
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [showWelcome]);

  if (data.loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-48 bg-muted rounded-3xl" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-32 bg-muted rounded-2xl" />)}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => <div key={i} className="h-80 bg-muted rounded-2xl" />)}
        </div>
      </div>
    );
  }

  const totalValue = data.analytics?.total_value || 0;
  const totalInvested = data.analytics?.total_invested || 0;
  const totalPnl = data.analytics?.total_pnl || 0;
  const totalPnlPct = data.analytics?.total_pnl_pct || 0;

  const sectorData = Object.entries(data.analytics?.sector_allocation || {}).map(([name, value]) => ({ name, value }));
  const topHoldingsData = (data.analytics?.top_holdings || []).map(h => ({
    name: h.ticker,
    weight: h.weight,
    pnl: h.pnl
  }));

  const COLORS = theme === 'dark' 
    ? ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#ec4899']
    : ['#2563eb', '#059669', '#7c3aed', '#d97706', '#dc2626', '#0891b2', '#db2777'];

  return (
    <div className="space-y-8 pb-10">
      {showWelcome && (
        <div className="relative overflow-hidden bg-primary rounded-[2.5rem] p-10 text-primary-foreground shadow-2xl shadow-primary/20 animate-in fade-in zoom-in duration-700">
          <div className="absolute top-0 right-0 -mt-20 -mr-20 w-96 h-96 bg-white/10 rounded-full blur-3xl animate-pulse-slow"></div>
          <div className="absolute bottom-0 left-0 -mb-20 -ml-20 w-64 h-64 bg-black/10 rounded-full blur-2xl"></div>
          
          <div className="relative flex flex-col md:flex-row items-center md:items-start space-y-6 md:space-y-0 md:space-x-8">
            <div className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center flex-shrink-0 shadow-inner group">
              <Sparkles className="text-white fill-white/20 group-hover:scale-110 transition-transform duration-500" size={40} />
            </div>
            <div className="text-center md:text-left">
              <h2 className="text-4xl font-black tracking-tight mb-2">Welcome back, {userName}</h2>
              <p className="text-primary-foreground/80 mt-2 text-xl font-medium max-w-2xl leading-relaxed">
                {data.analytics?.total_tickers === 0 
                  ? "Your intelligence engine is ready. Connect your first asset to unlock real-time portfolio scoring."
                  : `Your portfolio is performing with ${totalPnlPct >= 0 ? 'resilience' : 'caution'}. You have ${data.analytics?.total_tickers || 0} active signals worth ₹${totalValue.toLocaleString()}.`}
              </p>
              <div className="mt-8 flex flex-wrap justify-center md:justify-start gap-4">
                <Button size="lg" variant="secondary" onClick={() => navigate('/portfolio')} className="font-bold rounded-xl px-8 hover:scale-105 transition-all">
                  Optimize Assets
                </Button>
                <Button size="lg" variant="outline" onClick={() => navigate('/chat')} className="bg-white/10 border-white/20 hover:bg-white/20 text-white font-bold rounded-xl px-8 hover:scale-105 transition-all">
                  Consult AI
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
           <h1 className="text-4xl font-black text-foreground tracking-tight uppercase">Executive Intelligence</h1>
           <div className="flex items-center mt-2 space-x-3">
             <Badge variant="bullish" className="px-3 py-1 text-[10px] uppercase tracking-widest font-bold">Live Status</Badge>
             <div className="h-1 w-1 rounded-full bg-muted-foreground/30"></div>
             <p className="text-muted-foreground text-sm font-semibold tracking-wide uppercase">
               Strategy: <span className="text-primary">{data.riskProfile?.risk_tolerance || 'Balanced'}</span>
             </p>
           </div>
        </div>
        <div className="flex items-center space-x-3">
          <Button variant="outline" size="icon" onClick={() => fetchData()} className="rounded-xl hover:text-primary transition-all shadow-sm">
             <Activity size={18} />
          </Button>
          <Button onClick={() => navigate('/portfolio')} className="rounded-xl font-bold px-6 shadow-lg shadow-primary/20 hover:scale-[1.02] active:scale-95 transition-all">
             <Wallet size={18} className="mr-2" />
             Portfolio Portal
          </Button>
        </div>
      </div>

      {/* Portfolio Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricCard 
          title="Assets Under Management" 
          value={`₹${totalValue.toLocaleString(undefined, {maximumFractionDigits: 0})}`} 
          change={`${totalPnlPct >= 0 ? '+' : ''}${totalPnlPct.toFixed(1)}%`}
          isPositive={totalPnlPct >= 0}
          icon={PieChartIcon}
        />
        <MetricCard 
          title="Capital Invested" 
          value={`₹${totalInvested.toLocaleString(undefined, {maximumFractionDigits: 0})}`}
          subtitle="Lifetime Contribution"
          icon={Activity}
        />
        <MetricCard 
          title="Net Intelligence P&L" 
          value={`${totalPnl >= 0 ? '+' : ''}₹${totalPnl.toLocaleString(undefined, {maximumFractionDigits: 0})}`}
          isPositive={totalPnl >= 0}
          icon={TrendingUp}
        />
        <MetricCard 
          title="Total ROI Score" 
          value={`${totalPnlPct >= 0 ? '+' : ''}${totalPnlPct.toFixed(1)}%`}
          isPositive={totalPnlPct >= 0}
          icon={Sparkles}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sector Allocation */}
        <Card className="rounded-[2rem] border-none shadow-xl shadow-black/5 overflow-hidden group">
          <CardHeader className="pb-2 border-b border-border/50 bg-accent/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">Allocation Architecture</CardTitle>
              <PieChartIcon size={16} className="text-muted-foreground/50" />
            </div>
          </CardHeader>
          <CardContent className="pt-8">
            <div className="h-64 relative">
              {sectorData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={sectorData} innerRadius={75} outerRadius={100} paddingAngle={4} dataKey="value" nameKey="name" cornerRadius={6}>
                        {sectorData.map((entry, index) => (
                          <Cell key={`c-${index}`} fill={COLORS[index % COLORS.length]} className="hover:opacity-80 transition-opacity outline-none" stroke="none" />
                        ))}
                      </Pie>
                       <Tooltip 
                        contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '16px', color: 'hsl(var(--foreground))', boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' }}
                        itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                        formatter={(v) => [`${v}%`, 'Exposure']}
                       />
                    </PieChart>
                  </ResponsiveContainer>
                  <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <span className="text-3xl font-black text-foreground">{sectorData.length}</span>
                    <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">Sectors</span>
                  </div>
                </>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground bg-accent/30 rounded-[1.5rem] border-2 border-dashed border-border/50">
                  Insufficient signals
                </div>
              )}
           </div>
           <div className="grid grid-cols-2 gap-3 mt-8">
             {sectorData.slice(0, 4).map((s, i) => (
               <div key={s.name} className="flex items-center space-x-3 p-2.5 rounded-xl bg-accent/30 hover:bg-accent/50 transition-colors">
                 <div className="w-2.5 h-2.5 rounded-full shadow-sm" style={{ backgroundColor: COLORS[i % COLORS.length] }}></div>
                 <span className="text-[11px] font-bold text-foreground truncate uppercase tracking-tighter">{s.name}</span>
               </div>
             ))}
           </div>
          </CardContent>
        </Card>

        {/* Top Holdings */}
        <Card className="rounded-[2rem] border-none shadow-xl shadow-black/5 overflow-hidden group">
          <CardHeader className="pb-2 border-b border-border/50 bg-accent/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">Market Concentration</CardTitle>
              <BarChart3 size={16} className="text-muted-foreground/50" />
            </div>
          </CardHeader>
          <CardContent className="pt-8">
            <div className="h-64">
              {topHoldingsData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={topHoldingsData} layout="vertical" margin={{ left: -20, right: 20 }}>
                    <XAxis type="number" hide />
                    <YAxis type="category" dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={11} fontWeight="bold" width={60} axisLine={false} tickLine={false} />
                    <Tooltip 
                      cursor={{ fill: 'hsl(var(--accent))', opacity: 0.5 }}
                      contentStyle={{ backgroundColor: 'hsl(var(--card))', border: '1px solid hsl(var(--border))', borderRadius: '12px' }}
                      itemStyle={{ fontSize: '12px', fontWeight: 'bold' }}
                      formatter={(v) => [`${v}%`, 'Weight']}
                    />
                    <Bar dataKey="weight" fill="hsl(var(--primary))" radius={[0, 6, 6, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-muted-foreground bg-accent/30 rounded-[1.5rem] border-2 border-dashed border-border/50">
                  No concentrations
                </div>
              )}
           </div>
           <div className="mt-8 p-4 rounded-2xl bg-primary/5 border border-primary/10">
              <p className="text-[11px] text-muted-foreground leading-relaxed font-semibold uppercase tracking-tight">
                Top {topHoldingsData.length} holdings represent <span className="text-primary font-black">{topHoldingsData.reduce((acc, h) => acc + h.weight, 0).toFixed(1)}%</span> of intelligence footprint.
              </p>
           </div>
          </CardContent>
        </Card>

        {/* Risk Infrastructure */}
        <Card className="rounded-[2rem] border-none shadow-xl shadow-black/5 overflow-hidden group">
          <CardHeader className="pb-2 border-b border-border/50 bg-accent/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-xs font-black uppercase tracking-[0.2em] text-muted-foreground">Risk Infrastructure</CardTitle>
              <Shield size={16} className="text-muted-foreground/50" />
            </div>
          </CardHeader>
          <CardContent className="pt-8 space-y-6">
            <div className="grid grid-cols-2 gap-4">
              <RiskMetric label="Volatility" value={`${data.analytics?.volatility?.toFixed(1) || 0}%`} />
              <RiskMetric 
                label="Sharpe Ratio" 
                value={(data.analytics?.sharpe_ratio || 0).toFixed(2)} 
                highlight={(data.analytics?.sharpe_ratio || 0) >= 1 ? "emerald" : "amber"} 
              />
              <RiskMetric label="Max Drawdown" value={`-${(data.analytics?.max_drawdown || 0).toFixed(1)}%`} highlight="red" />
              <RiskMetric label="System Beta" value={(data.analytics?.beta || 1).toFixed(2)} />
            </div>
            
            <div className="bg-accent/30 rounded-[2rem] p-6 border border-border/50">
              <div className="flex justify-between items-end mb-4">
                <div>
                   <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest block mb-1">Diversification Score</span>
                   <Badge variant={(data.analytics?.diversification_score || 0) >= 70 ? "bullish" : (data.analytics?.diversification_score || 0) >= 40 ? "secondary" : "destructive"}>
                     {(data.analytics?.diversification_score || 0) >= 70 ? 'Optimal' : (data.analytics?.diversification_score || 0) >= 40 ? 'Moderate' : 'Concentrated'}
                   </Badge>
                </div>
                <span className="text-3xl font-black text-foreground">
                  {data.analytics?.diversification_score || 0}<span className="text-[10px] text-muted-foreground font-bold ml-1">/100</span>
                </span>
              </div>
              <div className="w-full bg-accent h-3 rounded-full overflow-hidden p-0.5">
                <div 
                  className={cn("h-full rounded-full transition-all duration-1000 ease-out", 
                    (data.analytics?.diversification_score || 0) >= 70 ? "bg-bullish" : 
                    (data.analytics?.diversification_score || 0) >= 40 ? "bg-amber-500" : "bg-destructive"
                  )}
                  style={{ width: `${data.analytics?.diversification_score || 0}%` }}
                ></div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Best/Worst Performers */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PerformanceCard 
          type="Top Performer" 
          asset={data.analytics?.best_performer} 
          icon={TrendingUp} 
          variant="bullish" 
        />
        <PerformanceCard 
          type="Performance Lag" 
          asset={data.analytics?.worst_performer} 
          icon={TrendingDown} 
          variant="bearish" 
        />
      </div>

      {/* Correlation Matrix */}
      <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 p-2 overflow-hidden">
        <CorrelationMatrix />
      </Card>

      {/* Portfolio Forecast Summary */}
      <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 p-2 overflow-hidden">
        <PortfolioForecastSummary />
      </Card>

      <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 overflow-hidden">
         <CardHeader className="px-8 py-6 border-b border-border/50 bg-accent/20">
           <div className="flex items-center justify-between">
             <div className="flex items-center space-x-3">
               <div className="p-2.5 bg-background rounded-xl shadow-sm">
                  <Activity size={18} className="text-primary" />
               </div>
               <div>
                 <CardTitle className="text-lg font-black uppercase tracking-tight">Portfolio Inventory</CardTitle>
                 <CardDescription className="text-[10px] font-bold uppercase tracking-widest">{data.analytics?.total_tickers || 0} active deployments</CardDescription>
               </div>
             </div>
             <Button variant="ghost" size="sm" onClick={() => fetchData()} className="text-[10px] font-black uppercase tracking-widest text-primary hover:text-primary hover:bg-primary/10">
                Resync Data
             </Button>
           </div>
         </CardHeader>
         <div className="overflow-x-auto custom-scrollbar">
           <table className="w-full min-w-[1000px]">
             <thead className="text-[10px] text-muted-foreground uppercase border-b border-border bg-accent/10">
               <tr>
                 <th className="px-8 py-5 text-left font-black tracking-widest">Asset Identity</th>
                 <th className="px-6 py-5 text-left font-black tracking-widest">Sector</th>
                 <th className="px-4 py-5 text-right font-black tracking-widest">Holdings</th>
                 <th className="px-4 py-5 text-right font-black tracking-widest">Avg Cost</th>
                 <th className="px-4 py-5 text-right font-black tracking-widest">Spot</th>
                 <th className="px-6 py-5 text-right font-black tracking-widest">Valuation</th>
                 <th className="px-8 py-5 text-right font-black tracking-widest">Performance</th>
                 <th className="px-6 py-5 text-right font-black tracking-widest">Weight</th>
                 <th className="px-8 py-5 text-center font-black tracking-widest">Intel</th>
               </tr>
             </thead>
             <tbody className="divide-y divide-border/50">
                {(data.analytics?.holdings || []).map((h, i) => (
                  <tr key={i} className="hover:bg-accent/30 transition-all group">
                    <td className="px-8 py-5 whitespace-nowrap">
                      <div className="flex items-center space-x-4">
                         <div className="w-11 h-11 rounded-xl bg-accent flex items-center justify-center font-black text-foreground group-hover:bg-background transition-all border border-transparent group-hover:border-border shadow-sm uppercase">
                           {h.ticker.slice(0, 2)}
                         </div>
                         <div className="flex flex-col">
                           <span className="font-black text-foreground text-sm uppercase tracking-tight leading-none mb-1">{h.ticker}</span>
                           <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter truncate max-w-[140px]">{h.company_name || '-'}</span>
                         </div>
                      </div>
                    </td>
                    <td className="px-6 py-5 whitespace-nowrap">
                       <Badge variant="secondary" className="text-[9px] font-black uppercase tracking-tight py-0.5">
                        {h.sector || 'N/A'}
                       </Badge>
                    </td>
                    <td className="px-4 py-5 text-right font-bold text-sm tabular-nums text-muted-foreground">{h.quantity}</td>
                    <td className="px-4 py-5 text-right font-bold text-sm tabular-nums text-muted-foreground">₹{h.avg_price?.toLocaleString()}</td>
                    <td className="px-4 py-5 text-right font-black text-sm tabular-nums text-foreground">₹{h.current_price?.toLocaleString()}</td>
                    <td className="px-6 py-5 text-right whitespace-nowrap font-black text-sm tabular-nums text-foreground">₹{h.current_value?.toLocaleString()}</td>
                    <td className="px-8 py-5 text-right whitespace-nowrap">
                      <div className={cn("flex flex-col items-end font-black tabular-nums", h.pnl >= 0 ? 'text-bullish' : 'text-destructive')}>
                        <span className="text-sm flex items-center">
                          {h.pnl >= 0 ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
                          {h.pnl_pct?.toFixed(2)}%
                        </span>
                        <span className="text-[10px] font-bold opacity-70 uppercase tracking-tighter">₹{Math.abs(h.pnl)?.toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="px-6 py-5 text-right">
                       <div className="flex flex-col items-end">
                         <span className="text-sm font-black text-muted-foreground tabular-nums">{h.weight?.toFixed(1) || 0}%</span>
                         <div className="w-16 bg-accent h-1.5 rounded-full mt-2 overflow-hidden p-0.5">
                           <div className="bg-primary h-full rounded-full" style={{ width: `${h.weight}%` }}></div>
                         </div>
                       </div>
                    </td>
                    <td className="px-8 py-5 text-center">
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => navigate(`/stock/${h.ticker}`)}
                        className="rounded-xl hover:bg-primary hover:text-white transition-all active:scale-95 shadow-sm"
                      >
                        <Search size={16} />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
           </table>
         </div>
         {data.analytics?.holdings?.length === 0 && (
           <div className="px-8 py-24 text-center flex flex-col items-center bg-accent/5">
              <div className="w-24 h-24 rounded-full bg-accent flex items-center justify-center mb-8 animate-pulse">
                <Activity size={48} className="text-muted-foreground/30" />
              </div>
              <h4 className="text-2xl font-black text-foreground uppercase tracking-tight">Zero signals detected</h4>
              <p className="text-muted-foreground mt-3 max-w-sm mx-auto font-medium">Your intelligence platform is optimized but currently awaits your first asset deployment.</p>
              <Button 
                onClick={() => navigate('/portfolio')}
                size="lg"
                className="mt-10 rounded-2xl px-10 font-black tracking-widest uppercase shadow-xl shadow-primary/20"
              >
                Launch Assets
              </Button>
           </div>
         )}
      </Card>
    </div>
  );
}

function MetricCard({ title, value, change, subtitle, isPositive, icon: Icon }) {
  return (
    <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 group hover:shadow-2xl hover:shadow-primary/5 transition-all duration-500 cursor-default overflow-hidden">
       <div className="p-8 flex flex-col justify-between h-full relative">
         <div className="absolute -top-10 -right-10 p-4 opacity-[0.03] group-hover:opacity-[0.08] transition-all duration-700 group-hover:rotate-12 group-hover:scale-110">
           {Icon && <Icon size={180} />}
         </div>
         
         <div className="flex items-center justify-between mb-8 relative">
           <div className="p-3.5 rounded-2xl bg-primary/10 text-primary border border-primary/20 group-hover:bg-primary group-hover:text-primary-foreground transition-all duration-500 shadow-sm">
             {Icon && <Icon size={24} />}
           </div>
           {change && (
             <Badge variant={isPositive ? "bullish" : "destructive"} className="px-3 py-1 font-black text-[10px] shadow-sm">
               {isPositive ? <TrendingUp size={12} className="mr-1" /> : <TrendingDown size={12} className="mr-1" />}
               {change}
             </Badge>
           )}
         </div>
         
         <div className="relative">
           <span className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] block mb-2 opacity-70 group-hover:opacity-100 transition-opacity">{title}</span>
           <div className="flex items-baseline space-x-1">
             <span className="text-3xl font-black text-foreground tracking-tight tabular-nums">{value}</span>
           </div>
           {subtitle && (
             <p className="text-[10px] font-bold text-muted-foreground mt-4 flex items-center uppercase tracking-widest opacity-60 group-hover:opacity-100 transition-opacity">
               <span className="w-1.5 h-1.5 rounded-full bg-primary mr-2 shadow-sm animate-pulse"></span>
               {subtitle}
             </p>
           )}
         </div>
       </div>
    </Card>
  );
}

function RiskMetric({ label, value, highlight }) {
  const colorClass = highlight === 'emerald' ? 'text-bullish' : highlight === 'red' ? 'text-destructive' : highlight === 'amber' ? 'text-amber-500' : 'text-foreground';
  const bgClass = highlight === 'emerald' ? 'bg-bullish/5' : highlight === 'red' ? 'bg-destructive/5' : highlight === 'amber' ? 'bg-amber-500/5' : 'bg-accent/30';

  return (
    <div className={cn("p-4 rounded-[1.5rem] border border-border/50 transition-all hover:bg-accent/50", bgClass)}>
      <span className="text-[9px] font-black text-muted-foreground uppercase tracking-widest block mb-1.5">{label}</span>
      <span className={cn("text-xl font-black tabular-nums", colorClass)}>{value}</span>
    </div>
  );
}

function PerformanceCard({ type, asset, icon: Icon, variant }) {
  return (
    <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 p-8 group overflow-hidden hover:shadow-2xl transition-all duration-500 cursor-default">
      <div className="absolute top-0 right-0 p-8 opacity-[0.02] group-hover:opacity-[0.05] transition-opacity duration-700">
        {Icon && <Icon size={120} />}
      </div>
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className={cn("p-3.5 rounded-2xl shadow-sm transition-all duration-500 group-hover:scale-110", 
            variant === 'bullish' ? 'bg-bullish/10 text-bullish group-hover:bg-bullish group-hover:text-white' : 'bg-destructive/10 text-destructive group-hover:bg-destructive group-hover:text-white')}>
            {Icon && <Icon size={24} />}
          </div>
          <h3 className="text-xs font-black text-foreground uppercase tracking-[0.2em]">{type}</h3>
        </div>
        {asset && (
          <Badge variant={variant} className="px-3 py-1 font-black text-[9px] uppercase tracking-widest">
            {variant === 'bullish' ? 'Optimal Yield' : 'Under Review'}
          </Badge>
        )}
      </div>
      {asset ? (
        <div className="flex justify-between items-center relative">
          <div>
            <p className="text-4xl font-black text-foreground tracking-tighter uppercase">{asset.ticker}</p>
            <p className="text-[10px] font-bold text-muted-foreground mt-1 uppercase tracking-widest truncate max-w-[180px]">{asset.company_name || '-'}</p>
          </div>
          <div className="text-right">
            <div className={cn("flex items-center justify-end font-black text-3xl tracking-tighter tabular-nums mb-1", variant === 'bullish' ? 'text-bullish' : 'text-destructive')}>
               {variant === 'bullish' ? <ArrowUpRight size={24} className="mr-1" /> : <TrendingDown size={24} className="mr-1" />}
               {asset.pnl_pct?.toFixed(2)}%
            </div>
            <p className="text-muted-foreground font-black text-xs tabular-nums tracking-widest uppercase">
              {asset.pnl >= 0 ? '+' : '-'}₹{Math.abs(asset.pnl)?.toLocaleString(undefined, {maximumFractionDigits: 0})}
            </p>
          </div>
        </div>
      ) : (
        <div className="py-8 text-center text-muted-foreground/40 font-bold uppercase tracking-widest italic border-2 border-dashed border-border/30 rounded-3xl bg-accent/5">
          Awaiting signals
        </div>
      )}
    </Card>
  );
}
