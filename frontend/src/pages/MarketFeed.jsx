import React, { useState, useEffect } from 'react';
import { api } from '../api/client';
import { Globe, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import clsx from 'clsx';

export default function MarketFeed() {
  const [feed, setFeed] = useState([]);
  const [newsSource, setNewsSource] = useState('pipeline');
  const [newsMessage, setNewsMessage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/market/news')
       .then(r => {
         setFeed(r.data.events || []);
         setNewsSource(r.data.source || 'pipeline');
         setNewsMessage(r.data.message);
       })
       .finally(() => setLoading(false));
  }, []);

  const getSentimentIcon = (sentiment) => {
    if (sentiment === 'positive') return <TrendingUp className="text-bullish" size={18} />;
    if (sentiment === 'negative') return <TrendingDown className="text-bearish" size={18} />;
    return <Minus className="text-text-muted" size={18} />;
  };

  return (
    <div className="space-y-6 max-w-4xl">
       <div className="pb-4 border-b border-terminal-border">
         <div className="flex items-center justify-between">
           <div>
             <h1 className="text-2xl font-bold text-text-primary flex items-center gap-3">
               <Globe className="text-accent-cyan" size={24} /> Market Intelligence 
             </h1>
             <p className="text-text-muted mt-1 text-sm">Real-time market events and analysis</p>
           </div>
           <span className={clsx(
             "text-xs px-3 py-1 rounded-full font-medium",
             newsSource === 'pipeline' ? "bg-green-900/50 text-green-400" : "bg-yellow-900/50 text-yellow-400"
           )}>
             {newsSource === 'pipeline' ? 'AI-Classified' : 'Live RSS'}
           </span>
         </div>
         {newsMessage && (
           <p className="text-xs text-text-muted mt-2">{newsMessage}</p>
         )}
       </div>

       {loading ? (
         <div className="space-y-3">
           {[1,2,3].map(i => <div key={i} className="h-24 bg-terminal-card animate-pulse rounded-xl" />)}
         </div>
       ) : feed.length === 0 ? (
         <div className="p-8 text-center text-text-muted bg-terminal-card border border-terminal-border rounded-xl">No events. Run the data pipeline.</div>
       ) : (
         <div className="space-y-3">
           {feed.map((event, i) => (
             <div key={i} className="bg-terminal-card border border-terminal-border p-4 rounded-xl hover:border-terminal-hover transition-colors">
                <div className="flex justify-between items-start mb-2">
                   <div className="flex items-center gap-2">
                     <span className={clsx("px-2 py-0.5 text-xs font-medium rounded", 
                        event.dominant_sentiment === 'positive' ? "bg-bullish/10 text-bullish" :
                        event.dominant_sentiment === 'negative' ? "bg-bearish/10 text-bearish" : 
                        "bg-terminal-border text-text-muted"
                     )}>
                        {event.sector} 
                     </span>
                     <span className="text-xs text-text-muted">{event.event_type?.replace('_', ' ')}</span>
                   </div>
                   <div className="flex items-center gap-1 text-sm">
                     {getSentimentIcon(event.dominant_sentiment)}
                     <span className="text-text-muted capitalize">{event.dominant_sentiment}</span>
                   </div>
                </div>
                
                <h3 className="text-text-primary font-medium mb-1">
                  {event.text?.split('.')[0]}.
                </h3>
                <p className="text-text-muted text-sm">
                  {event.text?.substring(event.text.indexOf('.') + 1).trim().slice(0, 100)}...
                </p>
                
                <div className="mt-3 flex items-center text-xs text-text-muted">
                   <span>{event.source}</span>
                   <span className="mx-2">•</span>
                   <span>{event.published}</span>
                </div>
             </div>
           ))}
         </div>
       )}
    </div>
  );
}
