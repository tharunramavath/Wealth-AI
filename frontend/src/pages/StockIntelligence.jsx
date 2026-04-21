import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { ArrowLeft, Activity, Zap, Shield, AlertTriangle, RefreshCw, ExternalLink, Target, PieChart } from 'lucide-react';
import ForecastChart from '../components/ForecastChart';
import LoadingProgress from '../components/LoadingProgress';

function formatINR(value) {
  if (value >= 10000000) {
    return `₹${(value / 10000000).toFixed(1)}Cr`;
  } else if (value >= 100000) {
    return `₹${(value / 100000).toFixed(1)}L`;
  } else if (value >= 1000) {
    return `₹${(value / 1000).toFixed(1)}K`;
  }
  return `₹${value.toLocaleString('en-IN')}`;
}

export default function StockIntelligence() {
  const { ticker } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingStep, setLoadingStep] = useState(1);
  const [loadingMessage, setLoadingMessage] = useState('Fetching stock data...');
  const eventSourceRef = useRef(null);
  const loadingRef = useRef(true);

  const fetchStockData = React.useCallback(async () => {
    setLoading(true);
    loadingRef.current = true;
    setLoadingStep(1);
    setLoadingMessage('Fetching stock data...');
    
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }
    
    const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    const userId = localStorage.getItem('user_id');
    const url = `${baseUrl}/market/stock/${encodeURIComponent(ticker)}/analyze/progressive${userId ? `?user_id=${userId}` : ''}`;
    
    eventSourceRef.current = new EventSource(url);
    
    eventSourceRef.current.addEventListener('progress', (event) => {
      try {
        const messageData = JSON.parse(event.data);
        setLoadingStep(messageData.step);
        setLoadingMessage(messageData.message);
      } catch (e) {
        console.error('SSE progress parse error:', e);
      }
    });
    
    eventSourceRef.current.addEventListener('complete', (event) => {
      try {
        const messageData = JSON.parse(event.data);
        setData(messageData);
        setLoading(false);
        loadingRef.current = false;
        eventSourceRef.current?.close();
      } catch (e) {
        console.error('SSE complete parse error:', e);
        setLoading(false);
        loadingRef.current = false;
      }
    });
    
    eventSourceRef.current.addEventListener('sse_error', (event) => {
      try {
        const messageData = JSON.parse(event.data);
        setData({ error: messageData.message });
        setLoading(false);
        loadingRef.current = false;
      } catch (e) {
        setData({ error: "Connection error. Please try again." });
        setLoading(false);
        loadingRef.current = false;
      }
    });
    
    eventSourceRef.current.onerror = () => {
      if (loadingRef.current) {
        setData({ error: "Connection error. Please try again." });
        setLoading(false);
        loadingRef.current = false;
      }
    };
  }, [ticker]);

  useEffect(() => {
    if (ticker) {
      fetchStockData();
    }
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, [ticker, fetchStockData]);

  if (loading) {
    return (
      <div className="max-w-md mx-auto mt-12">
        <LoadingProgress currentStep={loadingStep} totalSteps={5} />
      </div>
    );
  }

  if (data?.error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-6 text-center">
        <AlertTriangle className="w-12 h-12 text-red-400 mx-auto mb-3" />
        <p className="text-red-600 font-medium">{data.error}</p>
        <button onClick={() => navigate(-1)} className="mt-4 px-4 py-2 bg-red-100 hover:bg-red-200 text-red-600 rounded-lg">
          Go Back
        </button>
      </div>
    );
  }

  if (!data) return null;

  const { price, technicals, fundamentals, ai_analysis, portfolio_context } = data;
  const rsiColor = technicals.rsi > 70 ? "text-red-600" : technicals.rsi < 30 ? "text-green-600" : "text-gray-600";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate(-1)} className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
            <ArrowLeft size={20} className="text-gray-600" />
          </button>
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl font-bold text-gray-900">{data.company_name || data.ticker}</h1>
              <span className="px-2 py-1 bg-gray-100 text-gray-700 text-sm font-mono rounded">{data.ticker}</span>
              <a 
                href={`https://www.nseindia.com/get-quotes/equity?symbol=${data.ticker.replace('.NS', '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="p-1.5 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600"
              >
                <ExternalLink size={14} />
              </a>
            </div>
            <p className="text-gray-500 text-sm">{data.sector} • {data.industry}</p>
          </div>
        </div>
        <button onClick={fetchStockData} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Refresh Analysis">
          <RefreshCw size={18} className="text-gray-500" />
        </button>
      </div>

      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-end justify-between">
          <div>
            <span className="text-4xl font-bold text-gray-900">₹{price.current?.toLocaleString()}</span>
            <span className={`ml-3 text-lg font-semibold ${price.daily_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {price.daily_change >= 0 ? '+' : ''}{price.daily_change?.toFixed(2)}%
            </span>
          </div>
          <div className={`px-4 py-2 rounded-lg font-semibold ${technicals.trend === 'Bullish' ? 'bg-green-100 text-green-700' : technicals.trend === 'Bearish' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'}`}>
            {technicals.trend}
          </div>
        </div>
        <div className="grid grid-cols-4 gap-4 mt-6 pt-4 border-t border-gray-100">
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide">MA-20</p>
            <p className="text-gray-900 font-mono">₹{price.ma_20?.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide">MA-50</p>
            <p className="text-gray-900 font-mono">₹{price.ma_50?.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide">52W High</p>
            <p className="text-gray-900 font-mono">₹{price.high_52w?.toLocaleString()}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs uppercase tracking-wide">52W Low</p>
            <p className="text-gray-900 font-mono">₹{price.low_52w?.toLocaleString()}</p>
          </div>
        </div>
      </div>

      {portfolio_context && (
        <div className="bg-gradient-to-r from-purple-50 to-indigo-50 border border-purple-200 rounded-xl p-5">
          <div className="flex items-center space-x-2 mb-3">
            <Target className="text-purple-600" size={20} />
            <h3 className="font-semibold text-purple-900">Your Portfolio Context</h3>
            {data.from_cache && (
              <span className="ml-2 px-2 py-0.5 bg-purple-100 text-purple-600 text-xs rounded-full">Cached</span>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-gray-500 text-xs">Holdings</p>
              <p className="text-purple-900 font-bold">{portfolio_context.holdings_count} stocks</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Portfolio Value</p>
              <p className="text-purple-900 font-bold">{formatINR(portfolio_context.total_value)}</p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">{data.sector} Exposure</p>
              <p className={`font-bold ${portfolio_context.current_sector_exposure_pct > 25 ? 'text-red-600' : 'text-green-600'}`}>
                {portfolio_context.current_sector_exposure_pct}%
              </p>
            </div>
            <div>
              <p className="text-gray-500 text-xs">Existing in {data.sector}</p>
              <p className="text-gray-700 text-sm">{portfolio_context.existing_tickers?.length > 0 ? portfolio_context.existing_tickers.slice(0, 3).join(', ') : 'None'}</p>
            </div>
          </div>
          {portfolio_context.sector_allocation && Object.keys(portfolio_context.sector_allocation).length > 0 && (
            <div className="mt-4 pt-3 border-t border-purple-200">
              <p className="text-gray-500 text-xs mb-2 flex items-center gap-1">
                <PieChart size={12} /> Sector Allocation
              </p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(portfolio_context.sector_allocation).map(([sector, pct]) => (
                  <span key={sector} className={`px-2 py-1 text-xs rounded ${
                    sector === data.sector ? 'bg-purple-200 text-purple-800 font-medium' : 'bg-gray-100 text-gray-600'
                  }`}>
                    {sector}: {pct}%
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <ForecastChart ticker={ticker} />
        </div>

        <div className="space-y-6">
          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center space-x-2 mb-4">
              <Activity className="text-cyan-600" size={20} />
              <h3 className="font-semibold text-gray-900">Technical Pulse</h3>
            </div>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">RSI (14)</span>
                <div className="text-right">
                  <span className={`font-bold ${rsiColor}`}>{technicals.rsi}</span>
                  <span className="text-gray-400 text-xs ml-2">({technicals.rsi_signal})</span>
                </div>
              </div>
              <div className="w-full bg-gray-100 rounded-full h-2">
                <div className={`h-2 rounded-full ${technicals.rsi > 70 ? 'bg-red-500' : technicals.rsi < 30 ? 'bg-green-500' : 'bg-cyan-500'}`} style={{ width: `${Math.min(technicals.rsi, 100)}%` }}></div>
              </div>
              <div className="flex justify-between items-center pt-2 border-t border-gray-100">
                <span className="text-gray-600 text-sm">Volatility (30D)</span>
                <span className="font-mono text-gray-900">{technicals.volatility_30d}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Volume Ratio</span>
                <span className={`font-mono ${technicals.volume_ratio > 1.5 ? 'text-orange-600' : 'text-gray-900'}`}>
                  {technicals.volume_ratio}x
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">From 52W High</span>
                <span className="font-mono text-gray-900">{price.pct_from_high?.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-5">
            <div className="flex items-center space-x-2 mb-4">
              <Shield className="text-green-600" size={20} />
              <h3 className="font-semibold text-gray-900">Fundamentals</h3>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Market Cap</span>
                <span className="font-mono text-gray-900 text-sm">
                  {fundamentals.market_cap > 0 ? formatINR(fundamentals.market_cap) : 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">P/E Ratio</span>
                <span className={`font-mono ${fundamentals.pe_ratio > 30 ? 'text-orange-600' : 'text-gray-900'}`}>
                  {fundamentals.pe_ratio || 'N/A'}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Forward P/E</span>
                <span className="font-mono text-gray-900">{fundamentals.forward_pe || 'N/A'}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Dividend Yield</span>
                <span className="font-mono text-gray-900">{fundamentals.dividend_yield || 0}%</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Beta</span>
                <span className="font-mono text-gray-900">{fundamentals.beta}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">ROE</span>
                <span className={`font-mono ${fundamentals.roe > 15 ? 'text-green-600' : 'text-gray-900'}`}>
                  {fundamentals.roe || 0}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600 text-sm">Debt/Equity</span>
                <span className="font-mono text-gray-900">{fundamentals.debt_to_equity || 0}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {ai_analysis && typeof ai_analysis === 'object' ? (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Zap className="text-purple-600" size={20} />
              <h3 className="font-semibold text-gray-900">AI Analysis</h3>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs text-gray-400">{data.generated_at}</span>
              {ai_analysis.confidence_score && (
                <span className="px-2 py-0.5 bg-purple-100 text-purple-600 text-xs rounded-full">
                  {Math.round(ai_analysis.confidence_score * 100)}% confident
                </span>
              )}
            </div>
          </div>
          
          <div className="space-y-4">
            {ai_analysis.metric_insights && (
              <div className="bg-gradient-to-r from-slate-50 to-slate-100 rounded-lg p-4">
                <h4 className="text-slate-700 font-semibold text-sm mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-slate-500 rounded-full"></span>
                  Key Metric Insights
                </h4>
                <div className="space-y-2">
                  {ai_analysis.metric_insights.rsi && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">RSI:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.rsi}</span>
                    </div>
                  )}
                  {ai_analysis.metric_insights.moving_averages && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">MA Trend:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.moving_averages}</span>
                    </div>
                  )}
                  {ai_analysis.metric_insights.valuation && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">Valuation:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.valuation}</span>
                    </div>
                  )}
                  {ai_analysis.metric_insights.profitability && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">Profitability:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.profitability}</span>
                    </div>
                  )}
                  {ai_analysis.metric_insights.leverage && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">Leverage:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.leverage}</span>
                    </div>
                  )}
                  {ai_analysis.metric_insights.market_sensitivity && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-slate-600 min-w-[120px]">Sensitivity:</span>
                      <span className="text-slate-500">{ai_analysis.metric_insights.market_sensitivity}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {ai_analysis.bull_case && (
              <div className="bg-green-50 rounded-lg p-4 border border-green-100">
                <h4 className="text-green-700 font-semibold text-sm mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Bull Case
                </h4>
                <div className="space-y-2">
                  {ai_analysis.bull_case.catalysts && (
                    <div className="mb-3">
                      <span className="text-xs font-medium text-green-600 uppercase">Key Catalysts</span>
                      <ul className="mt-1 space-y-1">
                        {ai_analysis.bull_case.catalysts.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-green-700">
                            <span className="w-1.5 h-1.5 bg-green-500 rounded-full mt-1.5 flex-shrink-0"></span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {ai_analysis.bull_case.trend_continuation && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-green-600 min-w-[140px]">Trend:</span>
                      <span className="text-green-700">{ai_analysis.bull_case.trend_continuation}</span>
                    </div>
                  )}
                  {ai_analysis.bull_case.upside_potential && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-green-600 min-w-[140px]">Upside:</span>
                      <span className="text-green-700">{ai_analysis.bull_case.upside_potential}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {ai_analysis.bear_case && (
              <div className="bg-red-50 rounded-lg p-4 border border-red-100">
                <h4 className="text-red-700 font-semibold text-sm mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-red-500 rounded-full"></span>
                  Bear Case
                </h4>
                <div className="space-y-2">
                  {ai_analysis.bear_case.risks && (
                    <div className="mb-3">
                      <span className="text-xs font-medium text-red-600 uppercase">Key Risks</span>
                      <ul className="mt-1 space-y-1">
                        {ai_analysis.bear_case.risks.map((item, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-red-700">
                            <span className="w-1.5 h-1.5 bg-red-500 rounded-full mt-1.5 flex-shrink-0"></span>
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {ai_analysis.bear_case.trend_reversal && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-red-600 min-w-[140px]">Reversal Risk:</span>
                      <span className="text-red-700">{ai_analysis.bear_case.trend_reversal}</span>
                    </div>
                  )}
                  {ai_analysis.bear_case.downside_risk && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-red-600 min-w-[140px]">Downside:</span>
                      <span className="text-red-700">{ai_analysis.bear_case.downside_risk}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {ai_analysis.portfolio_fit && (
              <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
                <h4 className="text-indigo-700 font-semibold text-sm mb-3 flex items-center gap-2">
                  <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                  Portfolio Fit
                </h4>
                <div className="space-y-2">
                  {ai_analysis.portfolio_fit.diversification && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-indigo-600 min-w-[140px]">Diversification:</span>
                      <span className="text-indigo-700">{ai_analysis.portfolio_fit.diversification}</span>
                    </div>
                  )}
                  {ai_analysis.portfolio_fit.suggested_size && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-indigo-600 min-w-[140px]">Suggested Size:</span>
                      <span className="text-indigo-700">{ai_analysis.portfolio_fit.suggested_size}</span>
                    </div>
                  )}
                  {ai_analysis.portfolio_fit.correlation_warning && (
                    <div className="flex items-start gap-2 text-sm">
                      <span className="font-medium text-indigo-600 min-w-[140px]">Correlation:</span>
                      <span className="text-indigo-700">{ai_analysis.portfolio_fit.correlation_warning}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {ai_analysis.verdict && (
              <div className={`rounded-lg p-4 border ${
                ai_analysis.verdict.recommendation === 'BUY' ? 'bg-green-50 border-green-200' :
                ai_analysis.verdict.recommendation === 'BEARISH' ? 'bg-red-50 border-red-200' :
                'bg-gray-100 border-gray-200'
              }`}>
                <div className="flex items-center gap-3">
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                    ai_analysis.verdict.recommendation === 'BUY' ? 'bg-green-500 text-white' :
                    ai_analysis.verdict.recommendation === 'BEARISH' ? 'bg-red-500 text-white' :
                    'bg-gray-500 text-white'
                  }`}>
                    {ai_analysis.verdict.recommendation}
                  </span>
                  <span className="text-sm text-gray-700">{ai_analysis.verdict.rationale}</span>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : typeof ai_analysis === 'string' ? (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-2">
              <Zap className="text-purple-600" size={20} />
              <h3 className="font-semibold text-gray-900">Personalized AI Insights</h3>
            </div>
            <span className="text-xs text-gray-400">{data.generated_at}</span>
          </div>
          <div className="prose prose-sm max-w-none">
            {ai_analysis.split('\n').map((line, i) => {
              const cleanLine = line.replace(/\*\*/g, '').trim();
              if (cleanLine) {
                return <p key={i} className="text-gray-700 text-sm">{cleanLine}</p>;
              }
              return null;
            })}
          </div>
        </div>
      ) : (
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-6 text-center">
          <Activity className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">AI analysis not available</p>
          <p className="text-gray-400 text-sm mt-1">Please ensure NVIDIA API key is configured</p>
        </div>
      )}
    </div>
  );
}
