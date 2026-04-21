import sys
import os
import json
import hashlib
import time
from datetime import datetime

import pandas as pd
from backend import database as db

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.nba_engine import generate_nba
from src.risk_engine import calculate_portfolio_risk
from src.chat_engine import answer_finance_query

NBA_CACHE = {}

def generate_cache_key(user_id, holdings, risk_profile, market_snapshot):
    data = json.dumps({
        "user_id": user_id,
        "holdings": sorted([h["ticker"] for h in holdings]),
        "risk_tolerance": risk_profile.get("risk_tolerance"),
        "goals": sorted(risk_profile.get("goals", [])),
        "market_snapshot": market_snapshot
    }, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()

def run_nba_for_user(user_id, force_refresh=False, triggering_event=None):
    """Bridge function between FastAPI backend and core ML logic (nba_engine.py)."""
    holdings = db.get_portfolio(user_id)
    if not holdings:
        return {"error": "Portfolio is empty"}
    
    risk_profile = db.get_risk_profile(user_id) or {"risk_tolerance": "moderate", "investment_horizon": "5 years", "goals": ["Growth"]}
    
    from src.nba_engine import get_hybrid_context, client, MODEL_NAME, enforce_compliance, validate_tickers, log_prediction
    import yfinance as yf
    
    tickers_in_portfolio = [h["ticker"] for h in holdings]
    market_snapshot = ""
    try:
        for ticker in tickers_in_portfolio[:5]:
            tick = yf.Ticker(ticker)
            info = tick.info
            market_snapshot += f"{ticker}:{info.get('currentPrice', 0)}:{info.get('regularMarketChangePercent', 0)}|"
    except:
        market_snapshot = "unavailable"
    
    if triggering_event:
        event_str = json.dumps({
            "headline": triggering_event.get("headline", ""),
            "sector": triggering_event.get("sector", ""),
            "severity": triggering_event.get("severity", ""),
            "event_type": triggering_event.get("event_type", "")
        }, sort_keys=True)
        event_hash = hashlib.md5(event_str.encode()).hexdigest()[:8]
        cache_key = generate_cache_key(user_id, holdings, risk_profile, event_hash)
    else:
        cache_key = generate_cache_key(user_id, holdings, risk_profile, market_snapshot)
        if not force_refresh and cache_key in NBA_CACHE:
            cached_result = NBA_CACHE[cache_key].copy()
            cached_result["from_cache"] = True
            cached_result["cache_key"] = cache_key
            return cached_result
    
    if cache_key in NBA_CACHE:
        cached_result = NBA_CACHE[cache_key].copy()
        cached_result["from_cache"] = True
        cached_result["cache_key"] = cache_key
        return cached_result
    
    result = _generate_nba_result(user_id, holdings, risk_profile, tickers_in_portfolio, market_snapshot, cache_key, triggering_event)
    
    NBA_CACHE[cache_key] = result.copy()
    
    if len(NBA_CACHE) > 100:
        oldest = min(NBA_CACHE.keys(), key=lambda k: NBA_CACHE[k].get("_cached_at", 0))
        del NBA_CACHE[oldest]
    
    return result

def _generate_nba_result(user_id, holdings, risk_profile, tickers_in_portfolio, market_snapshot, cache_key, triggering_event=None):
    import yfinance as yf
    from src.nba_engine import get_hybrid_context, client, MODEL_NAME, enforce_compliance, validate_tickers, log_prediction
    
    event_context = ""
    if triggering_event:
        event_context = f"""
---
## TRIGGERING MARKET EVENT
Headline: {triggering_event.get('headline', 'N/A')}
Sector: {triggering_event.get('sector', 'Unknown')}
Severity: {triggering_event.get('severity', 'Low')}
Event Type: {triggering_event.get('event_type', 'general_news')}
Sentiment: {triggering_event.get('sentiment', {})}
Source: {triggering_event.get('source', 'N/A')}
---
"""
    
    portfolio_data = []
    total_value = 0
    
    for h in holdings:
        try:
            tick = yf.Ticker(h["ticker"])
            hist = tick.history(period="1d", timeout=5)
            current_price = float(hist["Close"].iloc[-1]) if not hist.empty else h["avg_price"]
        except:
            current_price = h["avg_price"]
        
        value = h["quantity"] * current_price
        total_value += value
        portfolio_data.append({
            "ticker": h["ticker"],
            "company": h.get("company_name", ""),
            "sector": h.get("sector", "Other"),
            "quantity": h["quantity"],
            "avg_price": h["avg_price"],
            "current_price": current_price,
            "portfolio_weight": 0
        })
    
    # Calculate weights
    for p in portfolio_data:
        p["portfolio_weight"] = round((p["quantity"] * p["current_price"]) / total_value * 100, 1) if total_value > 0 else 0
    
    # Calculate portfolio analytics
    total_invested = sum(h["quantity"] * h["avg_price"] for h in holdings)
    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    # Sector allocation
    sector_data = {}
    for p in portfolio_data:
        sector = p["sector"] or "Other"
        sector_data[sector] = sector_data.get(sector, 0) + (p["quantity"] * p["current_price"])
    
    sector_allocation = {k: round(v / total_value * 100, 1) for k, v in sector_data.items()} if total_value else {}
    
    # Top holdings
    top_holdings = sorted(portfolio_data, key=lambda x: x["portfolio_weight"], reverse=True)[:5]
    
    # Best/worst performers
    for p in portfolio_data:
        p["pnl"] = (p["current_price"] - p["avg_price"]) * p["quantity"]
        p["pnl_pct"] = ((p["current_price"] - p["avg_price"]) / p["avg_price"] * 100) if p["avg_price"] > 0 else 0
    
    performers = sorted(portfolio_data, key=lambda x: x["pnl_pct"], reverse=True)
    best_performer = performers[0] if performers else None
    worst_performer = performers[-1] if performers else None
    
    # Diversification score
    diversification_score = 100
    if sector_allocation:
        max_sector = max(sector_allocation.values())
        if max_sector > 40:
            diversification_score -= (max_sector - 40) * 1.5
    
    if top_holdings:
        top_weight = top_holdings[0]["portfolio_weight"]
        if top_weight > 25:
            diversification_score -= (top_weight - 25) * 2
    
    diversification_score = max(0, min(100, round(diversification_score)))
    
    # Portfolio metrics
    portfolio_volatility = 22.0  # Simplified estimate
    
    # Fetch market intelligence
    tickers_in_portfolio = [h["ticker"] for h in holdings]
    live_market_data = ""
    technical_analysis = ""
    
    try:
        if tickers_in_portfolio:
            tickers_str = " ".join(tickers_in_portfolio)
            market_data = yf.download(tickers_str, period="5d", progress=False)
            if market_data is not None and not market_data.empty:
                live_market_data = f"\n--- LIVE MARKET DATA (Last 5 Days) ---\n{market_data[['Close', 'Volume']].tail(10).to_string()}\n"
                
            for ticker in tickers_in_portfolio[:5]:
                try:
                    tick = yf.Ticker(ticker)
                    info = tick.info
                    price = info.get('currentPrice') or info.get('regularMarketPrice', 'N/A')
                    change = info.get('regularMarketChangePercent', 0)
                    ma50 = info.get('fiftyDayAverage', 'N/A')
                    ma200 = info.get('twoHundredDayAverage', 'N/A')
                    volume = info.get('averageVolume', 0)
                    technical_analysis += f"{ticker}: Price=${price}, Change={change:.2f}%, 50MA=${ma50}, 200MA=${ma200}, Vol={volume:,}\n"
                except:
                    pass
    except Exception as e:
        print(f"⚠️ Live market data fetch error: {e}")
    
    query = f"News regarding {', '.join(tickers_in_portfolio)} and {', '.join(risk_profile.get('goals', ['General Growth']))}"
    context_data = get_hybrid_context(query, {h["ticker"]: h["quantity"] * h["avg_price"] for h in holdings})
    
    combined_market_context = context_data.get('vector_context', '')
    if live_market_data:
        combined_market_context += live_market_data
    
    num_sources = len(context_data.get('sources', []))
    
    if not combined_market_context.strip():
        combined_market_context = "No historical market context available. Provide recommendations based on general market knowledge and portfolio goals."
    
    # Format portfolio for prompt
    portfolio_str = "\n".join([
        f"- {p['ticker']}: {p['company']}, Sector: {p['sector']}, Qty: {p['quantity']}, Avg: ₹{p['avg_price']}, Current: ₹{p['current_price']:.2f}, Weight: {p['portfolio_weight']}%"
        for p in portfolio_data
    ])
    
    # Sector allocation string
    sector_str = "\n".join([f"- {sector}: {weight}%" for sector, weight in sector_allocation.items()])
    
    prompt = f"""
You are an AI Wealth Advisor analyzing an investor's portfolio and recent market events.

Your task is to generate actionable investment insights.

Use the client profile, portfolio data, portfolio analytics, and recent market intelligence to produce a recommendation.

{event_context}

---

## Client Profile

Risk Tolerance: {risk_profile.get('risk_tolerance', 'moderate')}
Investment Horizon: {risk_profile.get('investment_horizon', '5 years')}
Investment Goal: {', '.join(risk_profile.get('goals', ['Growth']))}

---

## Portfolio Analytics

Total Portfolio Value: ₹{total_value:,.0f}
Total Invested: ₹{total_invested:,.0f}
Total Profit/Loss: ₹{total_pnl:,.0f} ({total_pnl_pct:.1f}%)
Portfolio Volatility: {portfolio_volatility}%
Diversification Score: {diversification_score}/100

Sector Allocation:
{sector_str}

Top Holdings (by weight):
{chr(10).join([f"- {h['ticker']}: {h['portfolio_weight']}%" for h in top_holdings]) if top_holdings else "N/A"}

Best Performer: {best_performer['ticker'] + " (" + str(round(best_performer['pnl_pct'], 1)) + "%)" if best_performer else "N/A"}
Worst Performer: {worst_performer['ticker'] + " (" + str(round(worst_performer['pnl_pct'], 1)) + "%)" if worst_performer else "N/A"}

---

## Client Portfolio

Portfolio Data:

{portfolio_str}

---

## Market Intelligence

{combined_market_context}

## Technical Analysis
{technical_analysis if technical_analysis else "No technical data available."}

Sources Found: {num_sources}

---

## Instructions

1. Analyze the market events and determine which sectors or companies may be affected.
2. Evaluate the portfolio exposure, diversification, and risk metrics.
3. Identify risks such as sector concentration, volatility, or macro impact.
4. Use technical indicators (RSI, price trends) to strengthen your analysis.
5. Generate a clear investment action aligned with the client's risk profile and investment horizon.

Possible actions:
- BUY
- SELL
- HOLD
- REBALANCE
- REDUCE EXPOSURE
- INCREASE EXPOSURE

---

## Constraints

- Do NOT invent stocks or tickers.
- Only refer to assets present in the portfolio.
- Ensure recommendations align with the client's risk tolerance.
- Focus on long-term wealth growth.
- Avoid extreme or speculative strategies.

---

## Output Format (STRICT JSON)

Follow this reasoning process, then return ONLY valid JSON:

### Step 1: Market Analysis
Identify 1-2 key market signals from the provided data.

### Step 2: Portfolio Assessment
List specific strengths/weaknesses of this portfolio based on the analytics.

### Step 3: Action Decision
Based on steps 1 & 2, select ONE action from: BUY, SELL, HOLD, REBALANCE

### Step 4: Confidence Calibration
Assign confidence score based on: number of supporting signals (0-3 sources = low, 4+ sources = high), technical alignment, risk profile fit.

Return ONLY valid JSON in this format:

{{
"reasoning": {{
    "market_signals": ["Signal 1", "Signal 2"],
    "portfolio_strengths": ["Strength 1", "Strength 2"],
    "portfolio_weaknesses": ["Weakness 1"],
    "risk_alignment": "How this action fits the risk tolerance"
}},
"market_insight": "Brief explanation of the current market situation.",
"portfolio_impact": "Explain how the market events affect the client's portfolio.",
"next_best_action": {{
    "action": "BUY | SELL | HOLD | REBALANCE | REDUCE_EXPOSURE | INCREASE_EXPOSURE",
    "target_assets": ["TICKER1", "TICKER2"],
    "suggested_change": "Describe what to change in the portfolio allocation"
}},
"reasoning": "Explain why this action aligns with the client's risk tolerance and long-term goal.",
"confidence_score": 0.0
}}

Confidence Score Guidelines:
- 0.85-1.0: Very high confidence. Strong technical signals (RSI < 30 or > 70), multiple supporting news sources, clear market trend alignment with client goals.
- 0.70-0.85: High confidence. Good evidence from news/sentiment, reasonable technical alignment.
- 0.50-0.70: Moderate confidence. Some supporting data but mixed signals or limited sources.
- 0.30-0.50: Low confidence. Uncertain signals, limited data, conflicting indicators.
- 0.0-0.30: Very low confidence. No clear signals, rely on HOLD with caution.
"""
    
    start_time = time.time()
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an elite wealth advisor. Follow the reasoning steps carefully and always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2048,
            seed=42,
            response_format={"type": "json_object"}
        )
        result = json.loads(response.choices[0].message.content)
        result["sources"] = context_data.get("sources", [])
        result["cache_key"] = cache_key
        result["_cached_at"] = time.time()
        result["from_cache"] = False
        
        if triggering_event:
            result["triggering_event"] = {
                "headline": triggering_event.get("headline"),
                "sector": triggering_event.get("sector"),
                "severity": triggering_event.get("severity"),
                "event_type": triggering_event.get("event_type"),
                "sentiment": triggering_event.get("sentiment"),
                "source": triggering_event.get("source")
            }
        
        # Include analytics in result
        result["analytics"] = {
            "total_value": round(total_value, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "sector_allocation": sector_allocation,
            "top_holdings": [{"ticker": h["ticker"], "weight": h["portfolio_weight"]} for h in top_holdings],
            "portfolio_volatility": portfolio_volatility,
            "diversification_score": diversification_score,
            "best_performer": best_performer["ticker"] if best_performer else None,
            "worst_performer": worst_performer["ticker"] if worst_performer else None
        }
        
        # Validate compliance
        portfolio_dict = {h["ticker"]: h["quantity"] * h["avg_price"] for h in holdings}
        action_str = result.get("next_best_action", {}).get("action", "HOLD")
        
        allowed_tickers = ["HDFCBANK.NS", "RELIANCE.NS", "TCS.NS", "INFY.NS", "BHARTIARTL.NS", "ITC.NS", 
                          "NIFTYBEES.NS", "GOLDBEES.NS", "LIQUIDBEES.NS", "AAPL", "MSFT", "TSLA", 
                          "GOOGL", "AMZN", "SPY", "QQQ", "GLD", "TLT", "VNQ", "Cash"]
        
        target_assets = result.get("next_best_action", {}).get("target_assets", [])
        
        all_text_to_validate = " ".join(target_assets)
        all_text_to_validate += " " + result.get("market_insight", "")
        all_text_to_validate += " " + result.get("portfolio_impact", "")
        if isinstance(result.get("reasoning"), dict):
            all_text_to_validate += " " + str(result.get("reasoning", {}).get("market_signals", []))
        
        hallucination_flags = validate_tickers(all_text_to_validate, allowed_tickers)
        
        compliance_flags = enforce_compliance(risk_profile.get("risk_tolerance", "moderate"), portfolio_dict, action_str)
        
        all_flags = compliance_flags + hallucination_flags
        result["flags"] = all_flags
        result["is_compliant"] = len(all_flags) == 0
        
        latency = (time.time() - start_time) * 1000
        log_prediction(user_id, latency, result.get("confidence_score", 0), all_flags, action_str)

        return result
    except Exception as e:
        return {"error": str(e)}

def compute_risk_for_weights(weights_dict):
    """Bridge for RiskEngine"""
    try:
        metrics = calculate_portfolio_risk(weights_dict)
        metrics["weights"] = weights_dict
        return metrics
    except Exception as e:
        return {"volatility": 0.15, "sharpe_ratio": 1.1, "beta": 1.0, "max_drawdown": 0.20, "weights": weights_dict, "error": str(e)}

def answer_query(message, risk_profile, portfolio_list, conversation_history=None, recent_nba=None):
    """Bridge for Chat Engine - for backward compatibility"""
    try:
        return answer_finance_query(message, risk_profile, portfolio_list, conversation_history, recent_nba)
    except Exception as e:
        return f"I encountered an error accessing my tools: {str(e)}"
