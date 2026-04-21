import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import toast from 'react-hot-toast';
import { Plus, Trash2, ArrowRight, Activity, Wallet, History, AlertCircle, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { cn } from '../lib/utils';

export default function Portfolio() {
  const [portfolio, setPortfolio] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const navigate = useNavigate();
  const [newAsset, setNewAsset] = useState({ ticker: '', quantity: '', avg_price: '', date_bought: '' });
  const [tickerSuggestions, setTickerSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    Promise.all([
      api.get('/portfolio'),
      api.get('/portfolio/analytics')
    ]).then(([p, a]) => {
      setPortfolio(p.data);
      setAnalytics(a.data);
    }).catch(() => setAnalytics(null))
    .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const searchTickers = async (query) => {
    if (query.length < 2) {
      setTickerSuggestions([]);
      return;
    }
    try {
      const res = await api.get(`/ticker/search?q=${encodeURIComponent(query)}`);
      setTickerSuggestions(res.data);
    } catch {
      setTickerSuggestions([]);
    }
  };

  const handleTickerChange = (e) => {
    const val = e.target.value;
    setNewAsset({ ...newAsset, ticker: val });
    setShowSuggestions(true);
    searchTickers(val);
  };

  const selectSuggestion = (s) => {
    setNewAsset({ ...newAsset, ticker: s.symbol });
    setTickerSuggestions([]);
    setShowSuggestions(false);
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    const t = toast.loading('Synchronizing with Ledger...');
    try {
      await api.post('/portfolio', {
        ticker: newAsset.ticker.toUpperCase(),
        quantity: parseFloat(newAsset.quantity),
        avg_price: parseFloat(newAsset.avg_price),
        date_bought: newAsset.date_bought || null
      });
      toast.success('Asset integrated successfully', { id: t });
      loadData();
      setNewAsset({ ticker: '', quantity: '', avg_price: '', date_bought: '' });
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Integration failed';
      toast.error(msg, { id: t });
    }
  };

  const handleRemove = (ticker) => {
    api.delete(`/portfolio/${ticker}`).then(() => {
      toast.success(`${ticker} decommissioned`);
      loadData();
    });
  };

  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-10">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
        <div>
           <h1 className="text-4xl font-black text-foreground tracking-tight uppercase">Asset Inventory</h1>
           <div className="flex items-center mt-2 space-x-3">
             <Badge variant="outline" className="px-3 py-1 text-[10px] uppercase tracking-widest font-bold border-primary/20 text-primary">Master Ledger</Badge>
             <div className="h-1 w-1 rounded-full bg-muted-foreground/30"></div>
             <p className="text-muted-foreground text-sm font-semibold tracking-wide uppercase">
               Active Signals: <span className="text-foreground">{portfolio.length} Units</span>
             </p>
           </div>
        </div>
        <div className="flex items-center space-x-3">
           <Button variant="outline" onClick={() => navigate('/nba')} className="rounded-xl font-bold px-6 shadow-sm hover:scale-[1.02] transition-all">
              Intelligence Check
              <ArrowRight size={16} className="ml-2 text-primary" />
           </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Form and Health */}
        <div className="lg:col-span-4 space-y-8">
           <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 overflow-hidden">
             <CardHeader className="bg-accent/20 border-b border-border/50 p-8">
                <div className="flex items-center space-x-4">
                  <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                    <Plus size={24} />
                  </div>
                  <div>
                    <CardTitle className="text-lg font-black uppercase tracking-tight">Deploy Asset</CardTitle>
                    <CardDescription className="text-[10px] font-bold uppercase tracking-widest">Add to Core Portfolio</CardDescription>
                  </div>
                </div>
             </CardHeader>
             
             <CardContent className="p-8">
                <form onSubmit={handleAdd} className="space-y-6">
                  <div className="space-y-2">
                     <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Symbol Identification</label>
                     <div className="relative">
                       <Input 
                         required 
                         value={newAsset.ticker} 
                         onChange={handleTickerChange} 
                         placeholder="e.g. RELIANCE, TCS" 
                         className="h-12 rounded-xl bg-accent/30 border-none font-bold uppercase focus-visible:ring-primary/20"
                         onFocus={() => setShowSuggestions(true)} 
                       />
                       {showSuggestions && tickerSuggestions.length > 0 && (
                         <div className="absolute z-50 w-full mt-2 bg-card border border-border rounded-xl shadow-2xl max-h-60 overflow-hidden animate-in fade-in zoom-in-95 duration-200">
                           {tickerSuggestions.map((s) => (
                             <div key={s.symbol} onClick={() => { selectSuggestion(s); }} 
                                  className="px-4 py-3 hover:bg-accent cursor-pointer text-sm flex justify-between items-center group transition-colors border-b border-border last:border-b-0">
                               <div>
                                 <span className="font-black text-foreground group-hover:text-primary uppercase tracking-tight">{s.symbol}</span>
                                 <span className="text-[10px] text-muted-foreground block font-bold uppercase tracking-tighter truncate max-w-[180px]">{s.name}</span>
                               </div>
                               <Badge variant="secondary" className="text-[9px] uppercase font-black">{s.exchDisp || 'NSE'}</Badge>
                             </div>
                           ))}
                         </div>
                       )}
                     </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                     <div className="space-y-2">
                       <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Quantity</label>
                       <Input 
                         required 
                         type="number" 
                         step="any"
                         value={newAsset.quantity} 
                         onChange={e => setNewAsset({...newAsset, quantity: e.target.value})} 
                         placeholder="0.00"
                         className="h-12 rounded-xl bg-accent/30 border-none font-black focus-visible:ring-primary/20 tabular-nums" 
                       />
                     </div>
                      <div className="space-y-2">
                        <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Cost Basis (Avg)</label>
                        <div className="relative">
                          <Input 
                            required 
                            type="number" 
                            step="any"
                            value={newAsset.avg_price} 
                            onChange={e => setNewAsset({...newAsset, avg_price: e.target.value})} 
                            placeholder="0.00"
                            className="h-12 rounded-xl bg-accent/30 border-none font-black focus-visible:ring-primary/20 tabular-nums" 
                          />
                        </div>
                      </div>
                  </div>

                  <div className="space-y-2">
                    <label className="text-[10px] font-black text-muted-foreground uppercase tracking-[0.2em] ml-1">Acquisition Time</label>
                    <Input 
                      type="date" 
                      value={newAsset.date_bought} 
                      onChange={e => setNewAsset({...newAsset, date_bought: e.target.value})} 
                      className="h-12 rounded-xl bg-accent/30 border-none font-bold focus-visible:ring-primary/20" 
                    />
                  </div>

                  <Button type="submit" className="w-full h-14 rounded-2xl font-black uppercase tracking-widest shadow-xl shadow-primary/20 group">
                     <Plus size={18} className="mr-2 group-hover:scale-125 transition-transform" />
                     Initialize Position
                  </Button>
                </form>
             </CardContent>
           </Card>
           
           {analytics && (
             <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 overflow-hidden">
                <CardHeader className="bg-accent/20 border-b border-border/50 p-8">
                  <div className="flex items-center space-x-4">
                    <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary border border-primary/20">
                      <Shield size={24} />
                    </div>
                    <div>
                      <CardTitle className="text-lg font-black uppercase tracking-tight">Risk Pulse</CardTitle>
                      <CardDescription className="text-[10px] font-bold uppercase tracking-widest">Aggregated Health Metrics</CardDescription>
                    </div>
                  </div>
                </CardHeader>
                
                <CardContent className="p-8 space-y-4">
                  <div className="flex justify-between items-center p-4 rounded-2xl bg-accent/30 border border-border/50">
                    <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Volatility Index</span>
                    <span className="text-sm font-black text-foreground tabular-nums">{analytics.volatility ? `${analytics.volatility.toFixed(2)}%` : 'N/A'}</span>
                  </div>
                  <div className="flex justify-between items-center p-4 rounded-2xl bg-bullish/5 border border-bullish/20">
                    <span className="text-[10px] font-black text-bullish uppercase tracking-widest">Sharpe Efficiency</span>
                    <span className="text-sm font-black text-bullish tabular-nums">{analytics.sharpe_ratio || '0.00'}</span>
                  </div>
                  <div className="flex justify-between items-center p-4 rounded-2xl bg-destructive/5 border border-destructive/20">
                    <span className="text-[10px] font-black text-destructive uppercase tracking-widest">Max Drawdown</span>
                    <span className="text-sm font-black text-destructive tabular-nums">{analytics.max_drawdown ? `${Math.abs(analytics.max_drawdown).toFixed(2)}%` : 'N/A'}</span>
                  </div>
                </CardContent>
             </Card>
           )}
        </div>

        {/* Right Column: Holdings Table */}
         <div className="lg:col-span-8">
            <Card className="rounded-[2.5rem] border-none shadow-xl shadow-black/5 overflow-hidden min-h-[600px] flex flex-col">
               <CardHeader className="px-8 py-6 border-b border-border/50 bg-card">
                 <div className="flex items-center justify-between">
                   <div className="flex items-center space-x-4">
                      <div className="w-12 h-12 rounded-2xl bg-accent/50 flex items-center justify-center border border-border">
                        <Wallet size={24} className="text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-xl font-black uppercase tracking-tight">Ledger Holdings</CardTitle>
                        <CardDescription className="text-[10px] font-bold uppercase tracking-widest">Real-time valuation and performance</CardDescription>
                      </div>
                   </div>
                   <Button variant="ghost" size="sm" onClick={loadData} className="rounded-xl">
                      <History size={16} className={cn("mr-2", loading && "animate-spin")} />
                      <span className="text-[10px] font-black uppercase tracking-widest">Refresh</span>
                   </Button>
                 </div>
               </CardHeader>

               {portfolio.length === 0 && !loading ? (
                 <div className="flex-1 flex flex-col items-center justify-center p-20 text-center">
                    <div className="w-24 h-24 bg-accent/50 rounded-[40px] flex items-center justify-center mb-8 border border-border animate-pulse">
                      <Activity size={48} className="text-muted-foreground/30" />
                    </div>
                    <h4 className="text-2xl font-black text-foreground uppercase tracking-tight">Ledger is Empty</h4>
                    <p className="text-muted-foreground mt-3 max-w-sm font-medium">No positions detected in the master ledger. Deploy your first asset using the sidebar.</p>
                 </div>
               ) : (
                 <div className="flex-1 overflow-x-auto custom-scrollbar">
                  <table className="w-full min-w-[900px]">
                    <thead className="text-[10px] text-muted-foreground uppercase border-b border-border bg-accent/10">
                      <tr>
                        <th className="px-8 py-5 text-left font-black tracking-[0.15em]">Asset Identity</th>
                        <th className="px-4 py-5 text-left font-black tracking-[0.15em]">Sector</th>
                        <th className="px-4 py-5 text-right font-black tracking-[0.15em]">Inventory</th>
                        <th className="px-4 py-5 text-right font-black tracking-[0.15em]">Cost Basis</th>
                        <th className="px-4 py-5 text-right font-black tracking-[0.15em]">Market Spot</th>
                        <th className="px-4 py-5 text-right font-black tracking-[0.15em]">Unrealized Alpha</th>
                        <th className="px-8 py-5 text-center font-black tracking-[0.15em]">Controls</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/50">
                      {portfolio.map((h, i) => (
                        <tr key={i} className="hover:bg-accent/30 transition-all group">
                          <td className="px-8 py-5 whitespace-nowrap">
                            <div className="flex items-center space-x-4">
                               <div className="w-11 h-11 rounded-xl bg-accent flex items-center justify-center font-black text-foreground group-hover:bg-background transition-all border border-transparent group-hover:border-border shadow-sm uppercase">
                                 {h.ticker.slice(0, 2)}
                               </div>
                               <div>
                                 <span className="font-black text-foreground text-sm uppercase block leading-none mb-1">{h.ticker}</span>
                                 <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-tighter truncate max-w-[160px] block">{h.company_name || '-'}</span>
                               </div>
                            </div>
                          </td>
                          <td className="px-4 py-5 whitespace-nowrap">
                             <Badge variant="secondary" className="text-[9px] font-black uppercase tracking-tight py-0.5">
                              {h.sector || 'Unassigned'}
                             </Badge>
                          </td>
                          <td className="px-4 py-5 text-right whitespace-nowrap">
                             <span className="text-sm font-black text-muted-foreground tabular-nums">{h.quantity}</span>
                          </td>
                          <td className="px-4 py-5 text-right whitespace-nowrap">
                             <span className="text-sm font-bold text-muted-foreground tabular-nums">₹{h.avg_price?.toLocaleString()}</span>
                          </td>
                          <td className="px-4 py-5 text-right whitespace-nowrap">
                             <span className="text-sm font-black text-foreground tabular-nums">₹{h.current_price?.toLocaleString()}</span>
                          </td>
                          <td className="px-4 py-5 text-right whitespace-nowrap">
                            <div className={cn("flex flex-col items-end font-black tabular-nums", h.pnl_pct >= 0 ? 'text-bullish' : 'text-destructive')}>
                              <span className="text-sm">
                                {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(2)}%
                              </span>
                              <span className="text-[9px] font-bold opacity-70 uppercase tracking-widest">Yield Delta</span>
                            </div>
                          </td>
                          <td className="px-8 py-5 text-center whitespace-nowrap">
                            <Button 
                              variant="ghost" 
                              size="icon"
                              onClick={() => handleRemove(h.ticker)} 
                              className="rounded-xl hover:bg-destructive/10 hover:text-destructive transition-all"
                              title="Dissolve Position"
                            >
                              <Trash2 size={16} />
                            </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                 </div>
               )}
               
               {portfolio.length > 0 && (
                 <div className="p-6 bg-accent/10 border-t border-border/50">
                    <div className="flex items-center text-[10px] font-bold text-muted-foreground uppercase tracking-[0.2em] space-x-2">
                       <AlertCircle size={14} className="text-primary" />
                       <span>Ledger updated via real-time market data pipelines</span>
                    </div>
                 </div>
               )}
            </Card>
         </div>
      </div>
    </div>
  );
}
