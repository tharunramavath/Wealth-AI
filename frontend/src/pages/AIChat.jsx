import React, { useState, useEffect, useRef } from 'react';
import { api } from '../api/client';
import { Send, User, Bot, Loader2, RefreshCw, Lightbulb, PieChart, TrendingUp, AlertCircle, Sparkles, Brain, StopCircle, ArrowRight, Target, ShieldCheck, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Input } from '../components/ui/Input';
import { Badge } from '../components/ui/Badge';
import { useTheme } from '../hooks/use-theme';
import { cn } from '../lib/utils';

const QUICK_ACTIONS = [
  { id: 'risk', label: 'Analyze Risk', icon: AlertCircle, prompt: 'Analyze the risk profile of my portfolio and suggest improvements' },
  { id: 'rebalance', label: 'Rebalancing', icon: PieChart, prompt: 'Should I rebalance my portfolio? What changes do you recommend?' },
  { id: 'outlook', label: 'Market Outlook', icon: TrendingUp, prompt: 'What is the current market outlook and how does it affect my portfolio?' },
  { id: 'stocks', label: 'Stock Insights', icon: Lightbulb, prompt: 'Tell me about any interesting stock opportunities' },
];

export default function AIChat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentIntent, setCurrentIntent] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const { theme: _theme } = useTheme();
  const scrollRef = useRef(null);
  const abortControllerRef = useRef(null);

  useEffect(() => {
    api.get('/chat/history').then(r => setMessages(r.data.reverse())).catch(console.error);
  }, []);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const handleSend = async (e, customMsg = null) => {
    e?.preventDefault();
    const msgToSend = customMsg || input;
    if (!msgToSend.trim() || loading) return;
    
    const userId = localStorage.getItem('user_id');
    if (!userId) {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Please log in to use the AI assistant.' }]);
      return;
    }
    
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: msgToSend }]);
    setLoading(true);
    setIsStreaming(true);
    
    abortControllerRef.current = new AbortController();
    let assistantMsg = { role: 'assistant', content: '' };
    
    try {
      const response = await fetch(`${api.defaults.baseURL}/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'x-user-id': userId,
        },
        body: JSON.stringify({ message: msgToSend }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error('Stream failed');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      setMessages(prev => [...prev, assistantMsg]);
      let metaParsed = false;
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (!metaParsed && (data.__intent || data.__sources !== undefined)) {
                metaParsed = true;
                if (data.__intent) setCurrentIntent(data.__intent);
                if (data.__recommendations) {
                  try {
                    const recRes = await api.get('/chat/recommendations');
                    if (recRes.data.recommendations) {
                      setRecommendations(recRes.data.recommendations);
                    }
                  } catch (e) {
                    console.error('Failed to fetch recommendations:', e);
                  }
                }
                continue;
              }
              
              if (data.token) {
                assistantMsg.content += data.token;
                setMessages(prev => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { ...assistantMsg };
                  return updated;
                });
              }
              if (data.done) break;
            } catch (e) {
              console.error('Parse error:', e);
            }
          }
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        console.error('Streaming failed, fallback:', err);
        try {
          const fallbackRes = await api.post('/chat', { message: msgToSend });
          setMessages(prev => {
            const filtered = prev.filter((_, i) => i !== prev.length - 1);
            return [...filtered, { role: 'assistant', content: fallbackRes.data.answer }];
          });
        } catch (fallbackErr) {
          console.error('Fallback failed:', fallbackErr);
          setMessages(prev => {
            const filtered = prev.filter((_, i) => i !== prev.length - 1);
            return [...filtered, { role: 'assistant', content: 'Neural link interrupted. Please retry.' }];
          });
        }
      }
    } finally {
      setLoading(false);
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleQuickAction = (action) => {
    handleSend(null, action.prompt);
  };

  const stopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setLoading(false);
      setIsStreaming(false);
    }
  };

  return (
    <Card className="flex flex-col h-[calc(100vh-10rem)] rounded-[2.5rem] border-none shadow-2xl shadow-black/5 overflow-hidden group">
      <CardHeader className="bg-primary p-8 relative overflow-hidden flex-shrink-0">
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -mr-32 -mt-32 blur-3xl"></div>
        <div className="relative z-10 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 rounded-2xl bg-white/20 backdrop-blur-md flex items-center justify-center shadow-lg">
              <Brain className="text-white" size={28} />
            </div>
            <div>
              <CardTitle className="text-white text-xl font-black uppercase tracking-tight leading-none mb-1">Neural Advisor</CardTitle>
              <CardDescription className="text-white/70 text-[10px] font-bold uppercase tracking-widest">Active Intelligence Engine</CardDescription>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <div className="w-2 h-2 rounded-full bg-bullish animate-pulse shadow-[0_0_8px_hsl(var(--bullish))]"></div>
            <span className="text-[10px] font-black text-white uppercase tracking-widest opacity-80">Online</span>
          </div>
        </div>
      </CardHeader>

      <div className="flex-1 overflow-y-auto p-8 space-y-8 custom-scrollbar scroll-smooth bg-accent/5" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="h-full flex flex-col items-center justify-center space-y-12 animate-in fade-in zoom-in duration-700">
            <div className="text-center space-y-4">
              <div className="w-20 h-20 bg-accent rounded-[2rem] flex items-center justify-center mx-auto mb-6 shadow-inner border border-border/50">
                <Sparkles size={32} className="text-primary" />
              </div>
              <h3 className="text-3xl font-black text-foreground uppercase tracking-tight">How can I optimize your wealth today?</h3>
              <p className="text-muted-foreground font-medium max-w-sm mx-auto">Ask about risk anomalies, sector rotations, or neural portfolio scoring.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full max-w-2xl">
              {QUICK_ACTIONS.map((action) => (
                <button
                  key={action.id}
                  onClick={() => handleQuickAction(action)}
                  className="group flex items-center justify-between p-5 rounded-3xl bg-card border border-border hover:border-primary/50 hover:bg-accent/30 transition-all duration-300 text-left shadow-sm hover:shadow-xl hover:shadow-primary/5 active:scale-[0.98]"
                  disabled={loading}
                >
                  <div className="flex items-center space-x-4">
                    <div className="w-10 h-10 rounded-xl bg-accent group-hover:bg-primary group-hover:text-primary-foreground flex items-center justify-center transition-all duration-300">
                      <action.icon size={18} />
                    </div>
                    <span className="text-sm font-black text-foreground uppercase tracking-tight">{action.label}</span>
                  </div>
                  <ArrowRight size={16} className="text-muted-foreground group-hover:text-primary group-hover:translate-x-1 transition-all" />
                </button>
              ))}
            </div>
          </div>
        )}
        
        {messages.map((msg, i) => (
          <div key={i} className={cn("flex gap-4 animate-in fade-in slide-in-from-bottom-2 duration-300", msg.role === 'user' ? "flex-row-reverse" : "")}>
            <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm transition-transform", 
               msg.role === 'user' ? "bg-primary text-primary-foreground" : "bg-card border border-border"
            )}>
               {msg.role === 'user' ? <User size={20} /> : <Brain size={20} className="text-primary" />}
            </div>
            <div className={cn("px-6 py-4 rounded-[1.8rem] max-w-[85%] shadow-sm leading-relaxed", 
               msg.role === 'user' ? "bg-primary text-primary-foreground rounded-tr-none" : "bg-card border border-border text-foreground rounded-tl-none"
            )}>
               {msg.role === 'user' ? (
                 <p className="text-sm font-bold tracking-tight uppercase">{msg.content}</p>
               ) : (
                 <div className="text-sm">
                   {currentIntent === 'stock_recommendation' && recommendations && (
                     <RecommendationBlock recommendations={recommendations} />
                   )}
                   <div className="prose prose-sm dark:prose-invert max-w-none prose-p:font-medium prose-p:text-foreground prose-strong:font-black prose-strong:uppercase prose-strong:tracking-widest">
                     <ReactMarkdown>{msg.content}</ReactMarkdown>
                   </div>
                 </div>
               )}
            </div>
          </div>
        ))}
        
        {loading && (
          <div className="flex gap-4 animate-in fade-in duration-300">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-card border border-border shadow-sm">
               <Brain size={20} className="text-primary animate-pulse" />
            </div>
            <div className="px-6 py-4 bg-card border border-border rounded-[1.8rem] rounded-tl-none flex items-center gap-4">
               {isStreaming ? (
                 <>
                   <Loader2 className="animate-spin text-primary" size={16} />
                   <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Inference Streaming...</span>
                   <Button 
                     onClick={stopStreaming}
                     variant="ghost"
                     size="sm"
                     className="h-7 px-3 bg-destructive/10 text-destructive hover:bg-destructive hover:text-white rounded-lg transition-all"
                   >
                     <StopCircle size={12} className="mr-1.5" />
                     Abort
                   </Button>
                 </>
               ) : (
                 <>
                   <Loader2 className="animate-spin text-primary" size={16} />
                   <span className="text-[10px] font-black text-muted-foreground uppercase tracking-widest">Thinking Neural Logic...</span>
                 </>
               )}
            </div>
          </div>
        )}
      </div>

      <div className="p-6 bg-card border-t border-border flex-shrink-0">
        <form onSubmit={handleSend} className="flex items-center gap-4 max-w-5xl mx-auto relative">
           <Input 
              value={input} 
              onChange={e => setInput(e.target.value)} 
              placeholder="Query neural database for portfolio advice..." 
              className="h-16 rounded-2xl bg-accent/30 border-none pl-6 pr-16 text-base font-medium focus-visible:ring-primary/20 shadow-inner"
              disabled={loading}
           />
           <Button 
              type="submit" 
              disabled={!input.trim() || loading} 
              className="absolute right-2 top-2 bottom-2 w-12 h-12 rounded-xl shadow-lg shadow-primary/20"
              size="icon"
            >
              <Send size={20} className={cn("transition-transform", input.trim() ? "translate-x-0.5 -translate-y-0.5" : "")} />
           </Button>
        </form>
        <p className="text-[9px] font-black text-muted-foreground uppercase tracking-widest text-center mt-3 opacity-50">AI response may vary based on market volatility and neural inference confidence.</p>
      </div>
    </Card>
  );
}

function RecommendationBlock({ recommendations }) {
  return (
    <div className="mb-6 p-6 rounded-3xl bg-primary/5 border border-primary/10 overflow-hidden relative group">
      <div className="absolute top-0 right-0 p-4 opacity-[0.05] group-hover:scale-110 transition-transform duration-500">
        <Target size={100} />
      </div>
      <div className="flex items-center justify-between mb-6 relative z-10">
        <div className="flex items-center space-x-3">
          <Zap size={18} className="text-primary fill-primary/20" />
          <h4 className="font-black text-primary uppercase tracking-widest text-xs">Top Deployment Recommendations</h4>
        </div>
        <Badge variant="bullish" className="px-3 py-1 font-black text-[9px] tracking-[0.2em] uppercase">High Confidence</Badge>
      </div>
      <div className="overflow-x-auto relative z-10 custom-scrollbar pb-2">
        <table className="w-full text-[11px]">
          <thead>
            <tr className="text-left border-b border-primary/10">
              <th className="pb-3 pr-4 font-black uppercase text-muted-foreground tracking-widest">Asset</th>
              <th className="pb-3 pr-4 font-black uppercase text-muted-foreground tracking-widest">Sector</th>
              <th className="pb-3 pr-4 font-black uppercase text-muted-foreground tracking-widest">AI Score</th>
              <th className="pb-3 pr-4 font-black uppercase text-muted-foreground tracking-widest">Forecast</th>
              <th className="pb-3 text-right font-black uppercase text-muted-foreground tracking-widest">Price</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-primary/5">
            {recommendations.recommended_stocks?.map((stock, idx) => (
              <tr key={idx} className="group/row transition-colors hover:bg-primary/5">
                <td className="py-3 pr-4 font-black text-primary uppercase tracking-tight">{stock.ticker}</td>
                <td className="py-3 pr-4 font-bold text-foreground opacity-80">{stock.sector}</td>
                <td className="py-3 pr-4">
                  <span className={cn("font-black tabular-nums", stock.score >= 0.7 ? 'text-bullish' : stock.score >= 0.6 ? 'text-amber-500' : 'text-destructive')}>
                    {(stock.score * 10).toFixed(1)}/10
                  </span>
                </td>
                <td className={cn("py-3 pr-4 font-black tabular-nums", stock.returns_3m >= 0 ? 'text-bullish' : 'text-destructive')}>
                  {stock.returns_3m >= 0 ? '+' : ''}{stock.returns_3m}%
                </td>
                <td className="py-3 text-right font-black text-foreground tabular-nums opacity-90">₹{stock.current_price.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-3 mt-6 relative z-10">
        <Badge variant="outline" className="bg-background/50 border-primary/20 text-[9px] font-black uppercase">
          Diversification: <span className="text-primary ml-1">{recommendations.portfolio_summary?.diversification}</span>
        </Badge>
        <Badge variant="outline" className="bg-background/50 border-primary/20 text-[9px] font-black uppercase">
          Risk Tier: <span className="text-primary ml-1">{recommendations.portfolio_summary?.risk_level}</span>
        </Badge>
        <Badge variant="outline" className="bg-background/50 border-primary/20 text-[9px] font-black uppercase">
          Inference Conf: <span className="text-primary ml-1">{(recommendations.metadata?.confidence_score * 100).toFixed(0)}%</span>
        </Badge>
      </div>
    </div>
  );
}
