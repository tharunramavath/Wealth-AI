"""
FastAPI Backend — Financial Intelligence & NBA Platform
Routers: /auth, /portfolio, /nba, /market, /chat, /alerts, /simulation
"""

import sys, os
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import json

from backend import database as db
from backend.database import init_db

app = FastAPI(title="Financial Intelligence Platform API", version="2.0")

@app.on_event("startup")
async def startup_event():
    try:
        deleted = db.cleanup_expired_cache()
        if deleted > 0:
            print(f"Cleaned up {deleted} expired cache entries")
    except Exception as e:
        print(f"Cache cleanup error: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple token = user_id (for demo; swap with JWT in production)
def get_current_user(x_user_id: str = Header(...)):
    user = db.get_user(x_user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or missing user ID header")
    return user

@app.on_event("startup")
def startup():
    init_db()
    print("✅ Database initialized")

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {"status": "Financial Intelligence API running", "version": "2.0"}

@app.post("/cache/stock-analysis/clear")
def clear_stock_cache(ticker: str = None, user_id: str = None):
    deleted = db.clear_stock_analysis_cache(user_id=user_id or None, ticker=ticker or None)
    return {"message": f"Cleared {deleted} cache entries"}

# ─────────────────────────────────────────────────────────────────────────────
#  AUTH
# ─────────────────────────────────────────────────────────────────────────────
class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    country: str
    phone: Optional[str] = None
    occupation: Optional[str] = None
    experience_level: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

@app.post("/auth/signup")
def signup(body: SignupRequest):
    result = db.signup(body.name, body.email, body.password, body.country,
                       body.phone, body.occupation, body.experience_level)
    if not result["success"]:
        raise HTTPException(status_code=409, detail=result["error"])
    return result

@app.post("/auth/login")
def login(body: LoginRequest):
    print(f"[DEBUG] Login attempt for email: {body.email}")
    print(f"[DEBUG] Password length: {len(body.password)}")
    result = db.login(body.email, body.password)
    print(f"[DEBUG] Login result: {result}")
    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["error"])
    return result

@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user

# ─────────────────────────────────────────────────────────────────────────────
#  ONBOARDING / RISK PROFILE
# ─────────────────────────────────────────────────────────────────────────────
class RiskProfileRequest(BaseModel):
    risk_tolerance: str
    investment_horizon: str
    goals: List[str]
    liquidity_need: str
    portfolio_size: str

@app.post("/onboarding/risk-profile")
def save_risk_profile(body: RiskProfileRequest, user=Depends(get_current_user)):
    db.save_risk_profile(user["user_id"], body.risk_tolerance, body.investment_horizon,
                         body.goals, body.liquidity_need, body.portfolio_size)
    # Auto-create welcome alert
    db.create_alert(user["user_id"], "Welcome! Your investor profile is complete. Set up your portfolio next.", "success")
    return {"success": True}

@app.get("/onboarding/risk-profile")
def get_risk_profile(user=Depends(get_current_user)):
    profile = db.get_risk_profile(user["user_id"])
    return profile or {}

# ─────────────────────────────────────────────────────────────────────────────
#  PORTFOLIO
# ─────────────────────────────────────────────────────────────────────────────
SECTOR_LOOKUP = {
    "AAPL":"Technology","MSFT":"Technology","GOOGL":"Technology","AMZN":"Technology",
    "TSLA":"Technology","TCS.NS":"Technology","INFY.NS":"Technology","QQQ":"Technology",
    "HDFCBANK.NS":"Financials","SPY":"Broad Market","NIFTYBEES.NS":"Broad Market",
    "RELIANCE.NS":"Energy","GLD":"Commodity/Gold","GOLDBEES.NS":"Commodity/Gold",
    "TLT":"Bonds","LIQUIDBEES.NS":"Bonds","VNQ":"Real Estate",
    "BHARTIARTL.NS":"Telecom","ITC.NS":"Consumer",
}
def validate_ticker(ticker: str) -> bool:
    try:
        import yfinance as yf
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            tick = yf.Ticker(ticker)
            hist = tick.history(period="1d", timeout=5)
            if hist is not None and not hist.empty:
                return True
            if not any(ticker.endswith(suffix) for suffix in ['.NS', '.BO', '.SI']):
                tick_ns = yf.Ticker(f"{ticker}.NS")
                hist_ns = tick_ns.history(period="1d", timeout=5)
                return hist_ns is not None and not hist_ns.empty
            return False
    except Exception as e:
        print(f"Validation error: {e}")
        return False


def normalize_ticker(ticker: str) -> str:
    ticker = ticker.upper().strip()
    if not any(ticker.endswith(suffix) for suffix in ['.NS', '.BO', '.SI', '.SS', '.L', '.F', '.OL']):
        try:
            import yfinance as yf
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tick = yf.Ticker(ticker)
                hist = tick.history(period="1d", timeout=5)
                if hist is None or hist.empty:
                    tick_ns = yf.Ticker(f"{ticker}.NS")
                    hist_ns = tick_ns.history(period="1d", timeout=5)
                    if hist_ns is not None and not hist_ns.empty:
                        return f"{ticker}.NS"
        except:
            pass
    return ticker

def search_ticker(query: str) -> Optional[dict]:
    try:
        import yfinance as yf
        results = yf.Search(query, max_results=5).quotes
        if results:
            return {
                "symbol": results[0]["symbol"],
                "name": results[0].get("shortname") or results[0].get("longname"),
                "exchange": results[0]["exchange"]
            }
    except Exception:
        pass
    return None

def resolve_sector(ticker, asset_type):
    return SECTOR_LOOKUP.get(ticker.upper(), asset_type or "Other")

class HoldingRequest(BaseModel):
    ticker: str
    quantity: float
    avg_price: float
    date_bought: Optional[str] = None

@app.get("/portfolio")
def get_portfolio(user=Depends(get_current_user)):
    holdings = db.get_portfolio(user["user_id"])
    try:
        import yfinance as yf
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for h in holdings:
                if h["ticker"] == "Cash":
                    h["current_price"] = 1.0
                    h["pnl_pct"] = 0.0
                    continue
                ticker = h["ticker"]
                hist = None
                try:
                    tick = yf.Ticker(ticker)
                    hist = tick.history(period="1d")
                except:
                    pass
                if hist is None or hist.empty:
                    if not any(ticker.endswith(s) for s in ['.NS', '.BO', '.SI']):
                        try:
                            tick_ns = yf.Ticker(f"{ticker}.NS")
                            hist = tick_ns.history(period="1d")
                        except:
                            pass
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    h["current_price"] = round(hist["Close"].iloc[-1], 2)
                    if h["avg_price"] > 0:
                        h["pnl_pct"] = round((h["current_price"] - h["avg_price"]) / h["avg_price"] * 100, 2)
                    else:
                        h["pnl_pct"] = 0.0
                else:
                    h["current_price"] = h["avg_price"]
                    h["pnl_pct"] = 0.0
    except Exception as e:
        print(f"Portfolio price fetch error: {e}")
        for h in holdings:
            h.setdefault("current_price", h["avg_price"])
            h.setdefault("pnl_pct", 0.0)
    # Ensure company_name and date_bought are always present
    for h in holdings:
        h.setdefault("company_name", "")
        h.setdefault("date_bought", "")
    return holdings

@app.post("/portfolio")
def add_holding(body: HoldingRequest, user=Depends(get_current_user)):
    ticker = body.ticker.upper().strip()
    quantity = body.quantity
    avg_price = body.avg_price
    date_bought = body.date_bought or datetime.utcnow().isoformat()

    if not validate_ticker(ticker):
        search_result = search_ticker(body.ticker)
        if search_result:
            ticker = search_result["symbol"]
        else:
            normalized = normalize_ticker(ticker)
            if normalized != ticker and validate_ticker(normalized):
                ticker = normalized
            else:
                raise HTTPException(status_code=400, detail=f"Invalid ticker: '{body.ticker}'. Please enter a valid stock symbol or company name.")
    else:
        ticker = normalize_ticker(ticker)

    from backend.asset_metadata import get_asset_metadata
    metadata = get_asset_metadata(ticker)
    
    db.upsert_holding(user["user_id"], ticker, quantity, avg_price, date_bought, metadata)
    
    from src.stock_data import get_stock_price_history
    price_history = get_stock_price_history(ticker, days=365)
    if price_history:
        db.save_batch_price_history(user["user_id"], ticker, price_history)
    
    return {"success": True, "ticker": ticker, "metadata": metadata}

@app.get("/ticker/search")
def search_tickers(q: str):
    try:
        import yfinance as yf
        results = yf.Search(q, max_results=10).quotes
        if results:
            return [{"symbol": r["symbol"], "name": r.get("shortname") or r.get("longname"), "exchange": r["exchange"]} for r in results]
    except Exception:
        pass
    return []

@app.delete("/portfolio/{ticker}")
def remove_holding(ticker: str, user=Depends(get_current_user)):
    db.delete_holding(user["user_id"], ticker)
    return {"success": True}

@app.post("/portfolio/sync-history")
def sync_portfolio_history(user=Depends(get_current_user)):
    from src.stock_data import get_stock_price_history
    holdings = db.get_portfolio(user["user_id"])
    results = {"synced": [], "failed": [], "skipped": 0}
    
    for holding in holdings:
        ticker = holding["ticker"]
        existing_history = db.get_price_history(user["user_id"], ticker, days=30)
        
        if len(existing_history) >= 30:
            results["skipped"] += 1
            continue
        
        price_history = get_stock_price_history(ticker, days=365)
        if price_history:
            db.save_batch_price_history(user["user_id"], ticker, price_history)
            results["synced"].append(ticker)
        else:
            results["failed"].append(ticker)
    
    return results

@app.get("/portfolio/analytics")
def portfolio_analytics(user=Depends(get_current_user)):
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        return {"error": "No portfolio data. Add holdings first."}

    try:
        import pandas as pd
        import numpy as np
        import yfinance as yf
        
        # Fetch current prices for all holdings
        tickers = [h["ticker"] for h in holdings if h["ticker"] != "Cash"]
        current_prices = {}
        
        for h in holdings:
            if h["ticker"] == "Cash":
                current_prices["Cash"] = 1.0
                continue
            try:
                tick = yf.Ticker(h["ticker"])
                hist = tick.history(period="1d", timeout=5)
                if not hist.empty:
                    current_prices[h["ticker"]] = float(hist["Close"].iloc[-1])
                else:
                    current_prices[h["ticker"]] = h["avg_price"]
            except:
                current_prices[h["ticker"]] = h["avg_price"]
        
        # Calculate portfolio values
        total_invested = 0
        total_current_value = 0
        holding_details = []
        
        for h in holdings:
            current_price = current_prices.get(h["ticker"], h["avg_price"])
            invested = h["quantity"] * h["avg_price"]
            current_value = h["quantity"] * current_price
            pnl = current_value - invested
            pnl_pct = (pnl / invested * 100) if invested > 0 else 0
            
            total_invested += invested
            total_current_value += current_value
            
            holding_details.append({
                "ticker": h["ticker"],
                "company_name": h.get("company_name", ""),
                "sector": h.get("sector", "Other"),
                "quantity": h["quantity"],
                "avg_price": h["avg_price"],
                "current_price": current_price,
                "invested": round(invested, 2),
                "current_value": round(current_value, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
            })
        
        total_pnl = total_current_value - total_invested
        total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Calculate weights
        for h in holding_details:
            h["weight"] = round((h["current_value"] / total_current_value * 100), 2) if total_current_value > 0 else 0
        
        # Sector allocation
        sector_data = {}
        for h in holding_details:
            sector = h["sector"] or "Other"
            sector_data[sector] = sector_data.get(sector, 0) + h["current_value"]
        
        sector_allocation = {k: round(v / total_current_value * 100, 1) for k, v in sector_data.items()} if total_current_value else {}
        
        # Top holdings
        top_holdings = sorted(holding_details, key=lambda x: x["weight"], reverse=True)[:5]
        
        # Best and worst performers (excluding Cash)
        performers = sorted([h for h in holding_details if h["ticker"] != "Cash"], key=lambda x: x["pnl_pct"], reverse=True)
        best_performer = performers[0] if performers else None
        worst_performer = performers[-1] if performers else None
        
        # Diversification score
        diversification_score = 100
        if sector_allocation:
            max_sector = max(sector_allocation.values())
            if max_sector > 40:
                diversification_score -= (max_sector - 40) * 1.5
        
        top_weight = top_holdings[0]["weight"] if top_holdings else 0
        if top_weight > 25:
            diversification_score -= (top_weight - 25) * 2
        
        diversification_score = max(0, min(100, round(diversification_score)))
        
        # Risk metrics (simplified - based on sector volatility estimates)
        sector_volatility = {
            "Technology": 0.25,
            "Financial Services": 0.22,
            "Energy": 0.20,
            "Consumer Cyclical": 0.24,
            "Communication Services": 0.23,
            "Other": 0.20
        }
        
        portfolio_volatility = 0
        for h in holding_details:
            vol = sector_volatility.get(h["sector"], 0.20)
            portfolio_volatility += vol * (h["weight"] / 100)
        
        risk_free_rate = 0.065
        expected_return = total_pnl_pct / 100
        sharpe_ratio = (expected_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # Beta (simplified estimate)
        beta = 1.0 + (portfolio_volatility - 0.20) * 2
        
        return {
            # Portfolio Overview
            "total_value": round(total_current_value, 2),
            "total_invested": round(total_invested, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            
            # Holdings details
            "holdings": holding_details,
            
            # Sector allocation
            "sector_allocation": sector_allocation,
            
            # Top holdings
            "top_holdings": top_holdings,
            
            # Performers
            "best_performer": best_performer,
            "worst_performer": worst_performer,
            
            # Risk metrics
            "volatility": round(portfolio_volatility * 100, 1),
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(-portfolio_volatility * 15, 1),
            "beta": round(beta, 2),
            
            # Diversification
            "diversification_score": diversification_score,
            
            "total_tickers": len(tickers),
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/portfolio/correlation")
def get_correlation_matrix(user=Depends(get_current_user), period: str = "1Y"):
    import pandas as pd
    import numpy as np
    
    period_days = {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(period, 365)
    
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        return {"error": "No portfolio holdings found. Add stocks to your portfolio first."}
    
    tickers = [h["ticker"] for h in holdings if h["ticker"] != "Cash"]
    if len(tickers) < 2:
        return {"error": "Need at least 2 stocks for correlation analysis. Add more holdings."}
    
    price_data = db.get_all_price_history(user["user_id"], days=period_days)
    
    available_tickers = [t for t in tickers if t in price_data and len(price_data[t]) > 10]
    
    if len(available_tickers) < 2:
        return {"error": f"Insufficient data. Need more historical data. Found: {len(available_tickers)} stocks"}
    
    prices_df = pd.DataFrame({
        ticker: pd.Series([d["close"] for d in price_data[ticker]], index=[d["date"] for d in price_data[ticker]])
        for ticker in available_tickers
    })
    
    returns_df = prices_df.pct_change().dropna()
    correlation_matrix = returns_df.corr()
    
    cov_matrix = returns_df.cov()
    
    stock_stats = {}
    for ticker in available_tickers:
        ticker_returns = returns_df[ticker].dropna()
        stock_stats[ticker] = {
            "mean_return": round(ticker_returns.mean() * 100, 4),
            "volatility": round(ticker_returns.std() * 100, 2),
            "positive_days": int((ticker_returns > 0).sum()),
            "negative_days": int((ticker_returns < 0).sum()),
        }
    
    insights = []
    
    high_corr_pairs = []
    low_corr_pairs = []
    neg_corr_pairs = []
    
    for i, t1 in enumerate(available_tickers):
        for j, t2 in enumerate(available_tickers):
            if i < j:
                corr_val = correlation_matrix.loc[t1, t2]
                if corr_val > 0.7:
                    high_corr_pairs.append((t1, t2, corr_val))
                elif corr_val < 0.2:
                    low_corr_pairs.append((t1, t2, corr_val))
                elif corr_val < -0.2:
                    neg_corr_pairs.append((t1, t2, corr_val))
    
    if high_corr_pairs:
        high_corr_pairs.sort(key=lambda x: x[2], reverse=True)
        insights.append({
            "type": "warning",
            "message": f"High correlation detected between {high_corr_pairs[0][0]} and {high_corr_pairs[0][1]} ({high_corr_pairs[0][2]:.2f}). Consider diversifying to reduce concentration risk."
        })
    
    if neg_corr_pairs:
        insights.append({
            "type": "opportunity",
            "message": f"NEGATIVE correlation ({neg_corr_pairs[0][0]} vs {neg_corr_pairs[0][1]}: {neg_corr_pairs[0][2]:.2f}) detected. These stocks may provide natural hedging."
        })
    
    if low_corr_pairs:
        insights.append({
            "type": "positive",
            "message": f"Low correlation between {low_corr_pairs[0][0]} and {low_corr_pairs[0][1]} ({low_corr_pairs[0][2]:.2f}). Good diversification potential."
        })
    
    matrix_data = []
    for ticker1 in available_tickers:
        row = {"ticker": ticker1}
        for ticker2 in available_tickers:
            row[ticker2] = round(correlation_matrix.loc[ticker1, ticker2], 3)
        matrix_data.append(row)
    
    return {
        "period": period,
        "period_days": period_days,
        "tickers": available_tickers,
        "matrix": matrix_data,
        "correlation_values": {t1: {t2: round(correlation_matrix.loc[t1, t2], 3) for t2 in available_tickers} for t1 in available_tickers},
        "stock_stats": stock_stats,
        "insights": insights,
        "data_points": len(returns_df),
        "date_range": {
            "start": returns_df.index.min() if len(returns_df) > 0 else None,
            "end": returns_df.index.max() if len(returns_df) > 0 else None,
        }
    }

# ─────────────────────────────────────────────────────────────────────────────
#  MARKET INTELLIGENCE
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/market/news")
def get_news():
    import pandas as pd
    
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "processed", "classified_events.csv")
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path).fillna("")
        events = df[["chunk_id","source","text","sector","event_type","dominant_sentiment","published"]].head(30).to_dict(orient="records")
        return {"events": events, "source": "pipeline", "message": None}
    
    from backend.news_fetcher import fetch_live_news
    events = fetch_live_news(max_articles=30)
    return {
        "events": events,
        "source": "live",
        "message": "Showing live news. Run data pipeline for AI-classified events."
    }

# ─────────────────────────────────────────────────────────────────────────────
#  NBA — AI RECOMMENDATION
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/nba/generate")
def generate_nba(
    user=Depends(get_current_user),
    x_force_refresh: Optional[str] = Header(None, alias="X-Force-Refresh")
):
    from backend.ai_engine import run_nba_for_user
    force_refresh = x_force_refresh and x_force_refresh.lower() == 'true'
    result = run_nba_for_user(user["user_id"], force_refresh=force_refresh)
    # Always save NBA result, even if error, for debugging
    db.save_nba(user["user_id"], result)
    
    # Handle next_best_action which can be string or dict
    nba_action = result.get("next_best_action", "")
    if isinstance(nba_action, dict):
        nba_action = nba_action.get("action", "HOLD")
    action_str = str(nba_action)[:80]
    
    if result.get("is_compliant"):
        db.create_alert(user["user_id"], f"New AI recommendation: {action_str}...", "ai")
    # Log error if present
    if "error" in result:
        print(f"NBA generation error for user {user['user_id']}: {result['error']}")
    return result

@app.get("/nba/history")
def nba_history(user=Depends(get_current_user)):
    return db.get_nba_history(user["user_id"])

# ─────────────────────────────────────────────────────────────────────────────
#  CACHE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
@app.post("/nba/cache/clear")
def clear_nba_cache():
    """Clear the in-memory NBA cache."""
    from backend.ai_engine import NBA_CACHE
    count = len(NBA_CACHE)
    NBA_CACHE.clear()
    return {"message": f"Cleared {count} cached NBA results"}

# ─────────────────────────────────────────────────────────────────────────────
#  EVENT-DRIVEN NBA
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/events/fetch")
def fetch_events(max_articles: int = 20):
    """Fetch latest market events from Alpha Vantage."""
    from src.event_fetcher import fetch_market_news
    events = fetch_market_news(max_articles=max_articles)
    return {"events": events, "count": len(events)}

@app.get("/events")
def get_events(user=Depends(get_current_user)):
    """Get cached recent events."""
    from src.trigger_engine import get_recent_events
    events = get_recent_events()
    return {"events": events, "count": len(events)}

@app.post("/events/scan")
def scan_events(user=Depends(get_current_user)):
    """Manually trigger event scan and NBA generation for affected portfolio sectors."""
    from src.event_fetcher import fetch_market_news, get_events_for_portfolio
    from src.structured_db import SECTOR_MAP
    from backend.ai_engine import run_nba_for_user
    
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        return {"events_scanned": 0, "nba_generated": 0, "message": "No portfolio holdings"}
    
    user_sectors = set()
    for h in holdings:
        sector = h.get("sector")
        if sector:
            user_sectors.add(sector)
    
    events = fetch_market_news(max_articles=30)
    
    relevant_events = [
        e for e in events 
        if (e.get("sector") in user_sectors and e.get("severity") in ["Critical", "High", "Medium"])
        or e.get("severity") in ["Critical", "High"]
    ]
    
    relevant_events = sorted(relevant_events, key=lambda x: 
        ({"Critical": 3, "High": 2, "Medium": 1, "Low": 0}.get(x.get("severity", "Low"), 0)),
        reverse=True
    )
    
    if not relevant_events:
        return {
            "events_scanned": len(events),
            "relevant_events": 0,
            "nba_generated": 0,
            "message": "No high-impact events affecting portfolio"
        }
    
    primary_event = relevant_events[0]
    result = run_nba_for_user(user["user_id"], force_refresh=True, triggering_event=primary_event)
    db.save_nba(user["user_id"], result)
    
    if result.get("is_compliant"):
        nba_action = result.get("next_best_action", "Hold")
        if isinstance(nba_action, dict):
            nba_action = nba_action.get("action", "Hold")
        db.create_alert(user["user_id"], f"Event-driven NBA: {str(nba_action)[:50]}...", "ai")
    
    return {
        "events_scanned": len(events),
        "relevant_events": len(relevant_events),
        "nba_generated": 1,
        "triggering_event": {
            "headline": primary_event.get("headline", "")[:100],
            "sector": primary_event.get("sector"),
            "severity": primary_event.get("severity")
        },
        "nba_result": result
    }

@app.post("/events/polling/start")
def start_polling():
    """Start background event polling (every 15 minutes)."""
    from src.trigger_engine import start_event_polling
    success = start_event_polling()
    return {"polling_active": success, "interval_minutes": 15}

@app.post("/events/polling/stop")
def stop_polling():
    """Stop background event polling."""
    from src.trigger_engine import stop_event_polling
    success = stop_event_polling()
    return {"polling_active": not success}

@app.get("/events/polling/status")
def polling_status():
    """Check if event polling is active."""
    from src.trigger_engine import _event_polling_thread
    is_running = _event_polling_thread is not None and _event_polling_thread.is_alive()
    return {"polling_active": is_running, "interval_minutes": 15}

# ─────────────────────────────────────────────────────────────────────────────
#  PORTFOLIO SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
class SimulationRequest(BaseModel):
    proposed_portfolio: dict  # {ticker: weight}

@app.post("/simulation/compare")
def simulate(body: SimulationRequest, user=Depends(get_current_user)):
    from backend.ai_engine import compute_risk_for_weights
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        raise HTTPException(400, "No portfolio found. Add holdings first.")
    # Build current weight map from value
    total = sum(h["quantity"] * h["avg_price"] for h in holdings)
    current_weights = {h["ticker"]: (h["quantity"] * h["avg_price"]) / total for h in holdings} if total else {}
    current_risk = compute_risk_for_weights(current_weights)
    proposed_risk = compute_risk_for_weights(body.proposed_portfolio)
    return {"current": current_risk, "proposed": proposed_risk, "current_weights": current_weights}

# ─────────────────────────────────────────────────────────────────────────────
#  WHAT-IF SCENARIO SIMULATION
# ─────────────────────────────────────────────────────────────────────────────
class ScenarioRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    proposed_holdings: List[dict]  # [{"ticker": "AAPL", "quantity": 10}, ...]
    is_nba_based: bool = False

@app.get("/simulation/scenarios")
def get_scenarios(user=Depends(get_current_user)):
    return db.get_scenarios(user["user_id"])

@app.post("/simulation/scenario/create")
def create_scenario(body: ScenarioRequest, user=Depends(get_current_user)):
    holdings = db.get_portfolio(user["user_id"])
    current_holdings = [
        {"ticker": h["ticker"], "quantity": h["quantity"], "avg_price": h["avg_price"], "sector": h.get("sector", "Unknown")}
        for h in holdings
    ]
    scenario_id = db.save_scenario(
        user_id=user["user_id"],
        name=body.name,
        description=body.description,
        proposed_holdings=body.proposed_holdings,
        current_holdings=current_holdings,
        is_nba_based=body.is_nba_based
    )
    return {"success": True, "scenario_id": scenario_id}

@app.get("/simulation/scenario/{scenario_id}")
def get_scenario(scenario_id: str, user=Depends(get_current_user)):
    scenario = db.get_scenario(user["user_id"], scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    return scenario

@app.post("/simulation/scenario/{scenario_id}/backtest")
def run_backtest(scenario_id: str, period: str = "6M", user=Depends(get_current_user)):
    from backend.backtest_engine import BacktestEngine, compare_scenarios
    from backend.performance import AsyncStockFetcher
    
    scenario = db.get_scenario(user["user_id"], scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    
    engine = BacktestEngine()
    
    current_result = engine.run_backtest(scenario["current_holdings"], period) if scenario["current_holdings"] else None
    proposed_result = engine.run_backtest(scenario["proposed_holdings"], period)
    
    if current_result and "error" not in current_result:
        impact = {
            "return_change": round(
                proposed_result.get("summary", {}).get("total_return", 0) - 
                current_result.get("summary", {}).get("total_return", 0), 2
            ),
            "volatility_change": round(
                proposed_result.get("summary", {}).get("volatility", 0) - 
                current_result.get("summary", {}).get("volatility", 0), 2
            ),
            "sharpe_change": round(
                proposed_result.get("summary", {}).get("sharpe_ratio", 0) - 
                current_result.get("summary", {}).get("sharpe_ratio", 0), 2
            ),
            "max_dd_change": round(
                proposed_result.get("summary", {}).get("max_drawdown", 0) - 
                current_result.get("summary", {}).get("max_drawdown", 0), 2
            ),
        }
    else:
        impact = {"return_change": 0, "volatility_change": 0, "sharpe_change": 0, "max_dd_change": 0}
    
    result = {
        "period": period,
        "period_days": {"1M": 30, "3M": 90, "6M": 180, "1Y": 365}.get(period, 180),
        "current": current_result if current_result else None,
        "proposed": proposed_result,
        "impact": impact,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    db.update_scenario_backtest(scenario_id, result)
    return result


@app.post("/simulation/scenario/{scenario_id}/monte-carlo")
def run_monte_carlo(scenario_id: str, horizon_days: int = 90, user=Depends(get_current_user)):
    from backend.monte_carlo import MonteCarloEngine
    
    scenario = db.get_scenario(user["user_id"], scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    
    engine = MonteCarloEngine(num_simulations=1000)
    
    result = engine.compare_scenarios_mc(
        current_holdings=scenario["current_holdings"],
        proposed_holdings=scenario["proposed_holdings"],
        horizon_days=horizon_days
    )
    
    return result


@app.post("/simulation/scenario/{scenario_id}/stress-test")
def run_stress_test(scenario_id: str, scenario_name: str = "2008_CRISIS", user=Depends(get_current_user)):
    from backend.risk_models import StressTestEngine
    
    scenario = db.get_scenario(user["user_id"], scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    
    engine = StressTestEngine()
    result = engine.run_stress_test(scenario["proposed_holdings"], scenario_name)
    
    return result


@app.get("/simulation/scenario/{scenario_id}/full-analysis")
def run_full_analysis(scenario_id: str, user=Depends(get_current_user)):
    from backend.backtest_engine import BacktestEngine
    from backend.monte_carlo import MonteCarloEngine
    from backend.risk_models import RiskScorer, MarketRegimeDetector
    
    scenario = db.get_scenario(user["user_id"], scenario_id)
    if not scenario:
        raise HTTPException(404, "Scenario not found")
    
    engine = BacktestEngine()
    mc_engine = MonteCarloEngine(num_simulations=500)
    risk_scorer = RiskScorer()
    regime_detector = MarketRegimeDetector()
    
    backtest_result = engine.run_backtest(scenario["proposed_holdings"], "6M")
    
    mc_result = mc_engine.run_simulation(scenario["proposed_holdings"], horizon_days=90)
    
    risk_analysis = risk_scorer.calculate_risk_score(scenario["proposed_holdings"])
    
    regime = regime_detector.detect_regime()
    
    return {
        "scenario_id": scenario_id,
        "scenario_name": scenario["name"],
        "backtest": backtest_result,
        "monte_carlo": mc_result,
        "risk_analysis": risk_analysis,
        "market_regime": regime,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.delete("/simulation/scenario/{scenario_id}")
def delete_scenario(scenario_id: str, user=Depends(get_current_user)):
    db.delete_scenario(user["user_id"], scenario_id)
    return {"success": True}

# ─────────────────────────────────────────────────────────────────────────────
#  FORECASTING (GARCH + Prophet)
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/forecast/{ticker}")
def get_ticker_forecast(
    ticker: str,
    days: int = 90,
    user=Depends(get_current_user)
):
    from src.forecasting import get_full_forecast
    from src.stock_data import get_stock_price_history
    import pandas as pd
    import numpy as np
    
    ticker = ticker.upper()
    
    if days <= 180:
        history_days = 365
    elif days <= 360:
        history_days = 730
    elif days <= 1095:
        history_days = 1460
    else:
        history_days = 1825
    
    price_data = db.get_price_history(user["user_id"], ticker, days=history_days)
    
    if not price_data or len(price_data) < 30:
        price_data = get_stock_price_history(ticker, days=history_days)
    
    min_required = min(history_days, max(30, days // 2))
    if not price_data or len(price_data) < min_required:
        return {"error": f"Insufficient historical data for {ticker}. Have {len(price_data) if price_data else 0} days, need {min_required}."}
    
    prices_df = pd.DataFrame(price_data)
    closes = pd.Series([d["close"] for d in price_data], index=[d["date"] for d in price_data])
    returns = closes.pct_change().dropna()
    
    result = get_full_forecast(prices_df, returns, forecast_days=days)
    result["ticker"] = ticker
    
    return result


@app.get("/forecast/portfolio/volatility")
def get_portfolio_volatility_forecast(
    days: int = 30,
    user=Depends(get_current_user)
):
    from src.forecasting import forecast_volatility_garch, calculate_var_cvar
    import pandas as pd
    
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        return {"error": "No portfolio holdings found."}
    
    tickers = [h["ticker"] for h in holdings if h["ticker"] != "Cash"]
    
    portfolio_returns = []
    
    for ticker in tickers:
        price_data = db.get_price_history(user["user_id"], ticker, days=365)
        if price_data and len(price_data) >= 30:
            closes = [d["close"] for d in price_data]
            ticker_returns = pd.Series(closes).pct_change().dropna()
            portfolio_returns.append(ticker_returns)
    
    if not portfolio_returns:
        return {"error": "Insufficient data for portfolio volatility forecast."}
    
    max_len = max(len(r) for r in portfolio_returns)
    aligned_returns = [r.reindex(range(max_len), fill_value=r.iloc[-1]) for r in portfolio_returns]
    
    combined_returns = pd.concat(aligned_returns, axis=1).mean(axis=1).dropna()
    
    volatility_result = forecast_volatility_garch(combined_returns, horizon=days)
    var_result = calculate_var_cvar(combined_returns)
    
    return {
        "ticker": "PORTFOLIO",
        "generated_at": volatility_result.get("generated_at", ""),
        "forecast_days": days,
        "volatility_forecast": volatility_result,
        "risk_metrics": var_result
    }

@app.get("/forecast/portfolio/price-summary")
def get_portfolio_forecast_summary(days: int = 30, user=Depends(get_current_user)):
    from src.forecasting import forecast_price_prophet
    import pandas as pd
    
    holdings = db.get_portfolio(user["user_id"])
    if not holdings:
        return {"error": "No portfolio holdings found."}
    
    summary = []
    
    for h in holdings:
        if h["ticker"] == "Cash":
            continue
        price_data = db.get_price_history(user["user_id"], h["ticker"], days=365)
        if price_data and len(price_data) >= 30:
            prices_df = pd.DataFrame(price_data)
            forecast = forecast_price_prophet(prices_df, days=days)
            if "error" not in forecast:
                summary.append({
                    "ticker": h["ticker"],
                    "current_price": forecast.get("last_price"),
                    "predicted_price": forecast.get("predicted_price"),
                    "expected_change_pct": forecast.get("expected_change_pct"),
                    "trend_direction": forecast.get("trend_direction"),
                    "upper_bound": forecast.get("upper_bound", [0])[-1] if forecast.get("upper_bound") else 0,
                    "lower_bound": forecast.get("lower_bound", [0])[-1] if forecast.get("lower_bound") else 0,
                })
    
    return {
        "forecasts": summary,
        "forecast_days": days
    }

# ─────────────────────────────────────────────────────────────────────────────
#  CHAT ASSISTANT
# ─────────────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat(body: ChatRequest, user=Depends(get_current_user)):
    from src.chat_engine import answer_finance_query
    
    portfolio = db.get_portfolio(user["user_id"])
    risk_profile = db.get_risk_profile(user["user_id"]) or {}
    conversation_history = db.get_chat_history(user["user_id"], limit=10)
    recent_nba = db.get_nba_history(user["user_id"], limit=3)
    
    db.save_chat_message(user["user_id"], "user", body.message)
    result = answer_finance_query(
        user_query=body.message,
        user_profile=risk_profile,
        portfolio=portfolio,
        conversation_history=conversation_history,
        recent_nba=recent_nba,
        user_id=user["user_id"]
    )
    answer = result.get("answer", "")
    sources = result.get("sources", [])
    cached = result.get("cached", False)
    db.save_chat_message(user["user_id"], "assistant", answer)
    return {"answer": answer, "sources": sources, "cached": cached}


@app.post("/chat/stream")
async def chat_stream(body: ChatRequest, user=Depends(get_current_user)):
    from src.chat_engine import answer_finance_query_streaming
    
    portfolio = db.get_portfolio(user["user_id"])
    risk_profile = db.get_risk_profile(user["user_id"]) or {}
    conversation_history = db.get_chat_history(user["user_id"], limit=10)
    recent_nba = db.get_nba_history(user["user_id"], limit=3)
    
    db.save_chat_message(user["user_id"], "user", body.message)
    
    full_response = []
    sources = []
    cached = False
    
    async def event_generator():
        nonlocal sources, cached
        for chunk in answer_finance_query_streaming(
            user_query=body.message,
            user_profile=risk_profile,
            portfolio=portfolio,
            conversation_history=conversation_history,
            recent_nba=recent_nba,
            user_id=user["user_id"]
        ):
            if chunk.startswith("{\"__sources\":"):
                try:
                    meta = json.loads(chunk)
                    sources = meta.get("__sources", [])
                    cached = meta.get("__cached", False)
                    yield f"data: {json.dumps({'sources': sources, 'cached': cached})}\n\n"
                except:
                    pass
            else:
                full_response.append(chunk)
                yield f"data: {json.dumps({'token': chunk})}\n\n"
        
        full_text = "".join(full_response)
        db.save_chat_message(user["user_id"], "assistant", full_text)
        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/chat/history")
def chat_history(user=Depends(get_current_user)):
    return db.get_chat_history(user["user_id"])

@app.post("/chat/save")
def chat_save(body: ChatRequest, user=Depends(get_current_user)):
    db.save_chat_message(user["user_id"], "assistant", body.message)
    return {"success": True}

@app.get("/chat/recommendations")
def get_latest_recommendations(user=Depends(get_current_user)):
    from src.chat_engine import REC_STREAMS
    if not REC_STREAMS:
        return {"recommendations": None}
    latest_hash = list(REC_STREAMS.keys())[-1] if REC_STREAMS else None
    if latest_hash:
        rec = REC_STREAMS.pop(latest_hash)
        return {"recommendations": rec}
    return {"recommendations": None}

# ─────────────────────────────────────────────────────────────────────────────
#  ALERTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/alerts")
def alerts(user=Depends(get_current_user)):
    return db.get_alerts(user["user_id"])

@app.post("/alerts/mark-read")
def mark_read(user=Depends(get_current_user)):
    db.mark_read(user["user_id"])
    return {"success": True}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTOR ROTATION / RRG ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/sector/rotation")
def get_sector_rotation(days: int = 90, user=Depends(get_current_user)):
    try:
        import json
        cache_path = "data/processed/sector_rotation_report.json"
        
        if os.path.exists(cache_path):
            file_mtime = os.path.getmtime(cache_path)
            cache_age = (datetime.now().timestamp() - file_mtime) / 3600
            
            if cache_age < 1:
                with open(cache_path, "r") as f:
                    return json.load(f)
        
        from src.data_pipeline import generate_sector_rotation_report
        report = generate_sector_rotation_report(days=days)
        return report
        
    except Exception as e:
        return {"error": str(e)}

@app.get("/sector/breadth")
def get_market_breadth(user=Depends(get_current_user)):
    try:
        rotation_data = get_sector_rotation(user=user)
        if "error" in rotation_data:
            return {"error": rotation_data["error"]}
        return rotation_data.get("market_breadth", {})
    except Exception as e:
        return {"error": str(e)}

@app.get("/sector/heatmap")
def get_sector_heatmap(user=Depends(get_current_user)):
    try:
        rotation_data = get_sector_rotation(user=user)
        if "error" in rotation_data:
            return {"error": rotation_data["error"]}
        
        heatmap_data = []
        for sector in rotation_data.get("rrg_coordinates", []):
            heatmap_data.append({
                "name": sector.get("name", ""),
                "ticker": sector.get("ticker", ""),
                "return": sector.get("sector_return", 0),
                "relative_return": sector.get("relative_return", 0),
                "quadrant": sector.get("quadrant", ""),
                "rs_ratio": sector.get("rs_ratio", 0),
                "momentum": sector.get("momentum", 0),
            })
        
        return {"sectors": heatmap_data, "generated_at": rotation_data.get("generated_at")}
        
    except Exception as e:
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
#  SECTOR DRILL-DOWN ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/sector/detail/{sector_ticker}")
def get_sector_detail(sector_ticker: str, user=Depends(get_current_user)):
    try:
        from src.data_pipeline import NIFTY_SECTORALS, SECTOR_CONSTITUENTS, BENCHMARK
        import yfinance as yf
        from datetime import datetime, timedelta
        import numpy as np
        
        sector_name = NIFTY_SECTORALS.get(sector_ticker, sector_ticker)
        constituents = SECTOR_CONSTITUENTS.get(sector_ticker, [])
        
        end_date = datetime.today()
        start_date = end_date - timedelta(days=90)
        
        price_history = []
        benchmark_history = []
        
        try:
            sector_hist = yf.Ticker(sector_ticker).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            if sector_hist is not None and not sector_hist.empty and "Close" in sector_hist.columns:
                sector_base = float(sector_hist["Close"].iloc[0])
                for i in range(len(sector_hist)):
                    date_val = sector_hist.index[i]
                    date_str = str(date_val)[:10]
                    price_history.append({
                        "date": date_str,
                        "price": round(float(sector_hist["Close"].iloc[i]), 2),
                        "return": round(float((sector_hist["Close"].iloc[i] / sector_base - 1) * 100), 2)
                    })
        except Exception:
            pass
        
        try:
            benchmark_hist = yf.Ticker(BENCHMARK).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            if benchmark_hist is not None and not benchmark_hist.empty and "Close" in benchmark_hist.columns:
                bench_base = float(benchmark_hist["Close"].iloc[0])
                for i in range(len(benchmark_hist)):
                    date_val = benchmark_hist.index[i]
                    date_str = str(date_val)[:10]
                    benchmark_history.append({
                        "date": date_str,
                        "price": round(float(benchmark_hist["Close"].iloc[i]), 2),
                        "return": round(float((benchmark_hist["Close"].iloc[i] / bench_base - 1) * 100), 2)
                    })
        except Exception:
            pass
        
        constituent_data = []
        for const in constituents:
            try:
                ticker_hist = yf.Ticker(const["ticker"]).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
                
                if ticker_hist is None or ticker_hist.empty or "Close" not in ticker_hist.columns:
                    continue
                
                close_prices = ticker_hist["Close"].dropna()
                if close_prices.empty:
                    continue
                
                current_price = float(close_prices.iloc[-1])
                prev_price = float(close_prices.iloc[-2]) if len(close_prices) > 1 else current_price
                price_20d_avg = float(close_prices.tail(20).mean()) if len(close_prices) >= 20 else current_price
                
                volumes = ticker_hist["Volume"].dropna()
                volume_avg = float(volumes.tail(20).mean()) if len(volumes) >= 20 else 0
                current_volume = float(volumes.iloc[-1]) if not volumes.empty else 0
                
                daily_return = float((current_price / prev_price - 1) * 100) if prev_price > 0 else 0
                volume_ratio = float(current_volume / volume_avg) if volume_avg > 0 else 0
                
                contribution = daily_return * const["weight"] / 100
                
                if current_price > price_20d_avg * 1.05:
                    tech_status = "Near High"
                elif current_price < price_20d_avg * 0.95:
                    tech_status = "Near Low"
                elif daily_return > 2:
                    tech_status = "Breakout"
                elif daily_return < -2:
                    tech_status = "Selloff"
                else:
                    tech_status = "Neutral"
                
                volume_signal = "Spike" if volume_ratio > 2 else ("Above Avg" if volume_ratio > 1.5 else "Normal")
                
                high_prices = ticker_hist["High"].dropna()
                high_52w = float(high_prices.max()) if not high_prices.empty else current_price * 1.2
                pct_from_high = float((high_52w - current_price) / high_52w * 100) if high_52w > 0 else 0
                
                momentum_20d = 0
                if len(close_prices) >= 21:
                    momentum_20d = float((close_prices.iloc[-1] / close_prices.iloc[-21] - 1) * 100)
                
                constituent_data.append({
                    "ticker": const["ticker"],
                    "name": const["name"],
                    "weight": const["weight"],
                    "current_price": round(current_price, 2),
                    "daily_change": round(daily_return, 2),
                    "contribution": round(contribution, 3),
                    "volume_ratio": round(volume_ratio, 2),
                    "volume_signal": volume_signal,
                    "tech_status": tech_status,
                    "pct_from_52w_high": round(pct_from_high, 1),
                    "momentum_20d": round(momentum_20d, 2),
                    "volume": int(current_volume),
                })
            except Exception:
                continue
        
        sector_return = price_history[-1]["return"] if price_history else 0
        bench_return = benchmark_history[-1]["return"] if benchmark_history else 0
        
        top_contributors = sorted(constituent_data, key=lambda x: x["contribution"], reverse=True)[:3]
        volume_spikes = [c for c in constituent_data if c["volume_signal"] == "Spike"]
        
        sector_return_30d = price_history[-30]["return"] if len(price_history) >= 30 else 0
        volatility_30d = 0
        if len(price_history) >= 30:
            returns_list = [p["return"] for p in price_history[-30:]]
            volatility_30d = round(float(np.std(returns_list) * np.sqrt(252)), 2)
        
        return {
            "sector_ticker": sector_ticker,
            "sector_name": sector_name,
            "quadrant": "Leading",
            "price_history": price_history,
            "benchmark_history": benchmark_history,
            "constituents": constituent_data,
            "weightage_data": [{"name": c["name"], "ticker": c["ticker"], "weight": c["weight"]} for c in constituent_data],
            "metrics": {
                "sector_return": round(sector_return, 2),
                "benchmark_return": round(bench_return, 2),
                "relative_return": round(sector_return - bench_return, 2),
                "return_30d": round(sector_return_30d, 2),
                "volatility_30d": volatility_30d,
            },
            "top_contributors": top_contributors,
            "volume_spikes": volume_spikes,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

# ─────────────────────────────────────────────────────────────────────────────
#  MARKET MOVERS ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/market/movers")
def get_market_movers(user=Depends(get_current_user)):
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        end_date = datetime.today()
        start_date = end_date - timedelta(days=5)
        
        tickers = {
            "RELIANCE.NS": "Reliance",
            "TCS.NS": "TCS",
            "HDFCBANK.NS": "HDFC Bank",
            "INFY.NS": "Infosys",
            "ICICIBANK.NS": "ICICI Bank",
            "SBIN.NS": "SBI",
            "BHARTIARTL.NS": "Bharti Airtel",
            "ITC.NS": "ITC",
            "KOTAKBANK.NS": "Kotak Bank",
            "LT.NS": "Larsen & Toubro",
            "SUNPHARMA.NS": "Sun Pharma",
            "TATAMOTORS.NS": "Tata Motors",
            "TATASTEEL.NS": "Tata Steel",
            "ADANIENT.NS": "Adani Enterprises",
            "MARUTI.NS": "Maruti Suzuki",
        }
        
        movers = []
        for ticker, name in tickers.items():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
                if hist is not None and not hist.empty and "Close" in hist.columns:
                    closes = hist["Close"].dropna()
                    if len(closes) >= 2:
                        current = float(closes.iloc[-1])
                        previous = float(closes.iloc[0])
                        change = ((current / previous) - 1) * 100
                        movers.append({
                            "ticker": ticker,
                            "name": name,
                            "price": round(current, 2),
                            "change": round(change, 2),
                        })
            except Exception as e:
                print(f"Error fetching {ticker}: {e}")
                continue
        
        if not movers:
            return {"error": "No market data available", "leaders": [], "laggards": []}
        
        movers_sorted = sorted(movers, key=lambda x: x["change"], reverse=True)
        
        leaders = movers_sorted[:5]
        laggards = movers_sorted[-5:][::-1]
        
        return {
            "leaders": leaders,
            "laggards": laggards,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        
    except Exception as e:
        return {"error": str(e), "leaders": [], "laggards": []}

# ─────────────────────────────────────────────────────────────────────────────
#  STOCK INTELLIGENCE ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────
@app.get("/market/stock/{ticker}/analyze")
def analyze_stock(
    ticker: str,
    user=Depends(get_current_user),
    x_force_refresh: Optional[str] = Header(None, alias="X-Force-Refresh")
):
    try:
        import yfinance as yf
        import numpy as np
        from datetime import datetime, timedelta
        
        ticker = ticker.upper().strip()
        user_id = user.get("user_id")
        force_refresh = x_force_refresh and x_force_refresh.lower() == 'true'
        
        cached = db.get_cached_stock_analysis(user_id, ticker) if not force_refresh else None
        if cached:
            return {
                "ticker": ticker,
                "company_name": cached.get("personalized_context", {}).get("company_name", ticker),
                "sector": cached.get("personalized_context", {}).get("sector", "Unknown"),
                "industry": cached.get("personalized_context", {}).get("industry", "Unknown"),
                "price": cached.get("personalized_context", {}).get("price", {}),
                "technicals": cached.get("personalized_context", {}).get("technicals", {}),
                "fundamentals": cached.get("personalized_context", {}).get("fundamentals", {}),
                "ai_analysis": cached["ai_analysis"],
                "personalized_for_you": True,
                "portfolio_context": cached.get("personalized_context", {}).get("portfolio_context"),
                "generated_at": cached["generated_at"],
                "from_cache": True,
            }
        
        end_date = datetime.today()
        start_date_60d = end_date - timedelta(days=60)
        start_date_90d = end_date - timedelta(days=90)
        
        stock = yf.Ticker(ticker)
        hist_60d = stock.history(start=start_date_60d.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        hist_90d = stock.history(start=start_date_90d.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
        
        if hist_60d.empty or "Close" not in hist_60d.columns:
            return {"error": f"No data available for ticker: {ticker}"}
        
        closes = hist_60d["Close"].dropna()
        volumes = hist_60d["Volume"].dropna()
        highs = hist_60d["High"]
        lows = hist_60d["Low"]
        
        current_price = float(closes.iloc[-1])
        prev_price = float(closes.iloc[-2]) if len(closes) > 1 else current_price
        daily_change = ((current_price / prev_price) - 1) * 100
        
        ma_20 = float(closes.tail(20).mean())
        ma_50 = float(closes.tail(50).mean()) if len(closes) >= 50 else ma_20
        
        delta = closes.diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.tail(14).mean()
        avg_loss = loss.tail(14).mean()
        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        
        returns_30d = closes.pct_change().tail(30)
        volatility_30d = float(returns_30d.std() * np.sqrt(252) * 100)
        
        high_52w = float(highs.max()) if not highs.empty else current_price * 1.3
        low_52w = float(lows.min()) if not lows.empty else current_price * 0.7
        pct_from_high = ((high_52w - current_price) / high_52w) * 100
        
        avg_volume_20d = float(volumes.tail(20).mean()) if len(volumes) >= 20 else float(volumes.mean())
        current_volume = float(volumes.iloc[-1]) if len(volumes) > 0 else 0
        volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
        
        trend = "Bullish" if current_price > ma_20 > ma_50 else "Bearish" if current_price < ma_20 < ma_50 else "Neutral"
        
        if rsi > 70:
            rsi_signal = "Overbought"
        elif rsi < 30:
            rsi_signal = "Oversold"
        else:
            rsi_signal = "Neutral"
        
        try:
            info = stock.info
            market_cap = info.get("marketCap", 0)
            pe_ratio = info.get("trailingPE", 0)
            forward_pe = info.get("forwardPE", 0)
            dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
            beta = info.get("beta", 1)
            debt_to_equity = info.get("debtToEquity", 0)
            roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0
            sector = info.get("sector", "Unknown")
            industry = info.get("industry", "Unknown")
            company_name = info.get("shortName", ticker)
        except:
            market_cap = 0
            pe_ratio = 0
            forward_pe = 0
            dividend_yield = 0
            beta = 1
            debt_to_equity = 0
            roe = 0
            sector = "Unknown"
            industry = "Unknown"
            company_name = ticker
        
        portfolio = db.get_portfolio(user_id)
        risk_profile = db.get_risk_profile(user_id)
        
        portfolio_context = None
        if portfolio:
            portfolio_sectors = {}
            portfolio_tickers = []
            total_value = 0
            
            batch_tickers = [h["ticker"] for h in portfolio]
            prices = db.get_portfolio_prices_batch(batch_tickers)
            
            for h in portfolio:
                h_price = prices.get(h["ticker"]) or h["avg_price"]
                value = h["quantity"] * h_price
                total_value += value
                portfolio_sectors[h["sector"]] = portfolio_sectors.get(h["sector"], 0) + value
                portfolio_tickers.append(h["ticker"])
            
            sector_allocation = {k: round(v/total_value*100, 1) for k, v in portfolio_sectors.items()}
            
            same_sector_value = portfolio_sectors.get(sector, 0)
            same_sector_pct = round(same_sector_value/total_value*100, 1) if total_value > 0 else 0
            
            portfolio_context = {
                "holdings_count": len(portfolio),
                "total_value": round(total_value, 2),
                "sector_allocation": sector_allocation,
                "existing_tickers": portfolio_tickers,
                "current_sector_exposure_pct": same_sector_pct,
                "sector": sector,
            }
        
        risk_tolerance = risk_profile.get("risk_tolerance", "moderate") if risk_profile else "moderate"
        investment_horizon = risk_profile.get("investment_horizon", "medium") if risk_profile else "medium"
        portfolio_size = risk_profile.get("portfolio_size", "medium") if risk_profile else "medium"
        
        def format_inr(value):
            if value >= 10000000:
                return f"₹{value/10000000:.1f}Cr"
            elif value >= 100000:
                return f"₹{value/100000:.1f}L"
            elif value >= 1000:
                return f"₹{value/1000:.1f}K"
            return f"₹{value:.0f}"
        
        def format_market_cap(value):
            if value >= 10000000:
                return f"₹{value/10000000:.0f}Cr"
            elif value >= 100000:
                return f"₹{value/100000:.0f}L"
            return f"₹{value:.0f}"
        
        portfolio_context_str = ""
        if portfolio_context:
            portfolio_context_str = f"""
INVESTOR PORTFOLIO CONTEXT:
- Risk Profile: {risk_tolerance.upper()} risk tolerance | {investment_horizon.upper()} investment horizon
- Portfolio Size: {portfolio_size}
- Current Holdings: {portfolio_context['holdings_count']} stocks worth {format_inr(portfolio_context['total_value'])}
- Sector Allocation: {', '.join([f"{k}: {v}%" for k, v in portfolio_context['sector_allocation'].items()])}
- Existing Exposure to {sector}: {portfolio_context['current_sector_exposure_pct']}%
- Existing Holdings: {', '.join(portfolio_context['existing_tickers'])}

ANALYSIS REQUIREMENTS:
1. FLAG if this stock would create >25% sector concentration
2. SUGGEST position size based on portfolio size (small: 2-5%, medium: 3-7%, large: 5-10%)
3. ASSESS correlation with existing holdings
4. RECOMMEND if it improves portfolio diversification
"""
        
        ai_analysis = None
        try:
            from openai import OpenAI
            import os
            from dotenv import load_dotenv
            load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
            nvidia_api_key = os.getenv("NVIDIA_API_KEY")
            if nvidia_api_key:
                client = OpenAI(
                    base_url="https://integrate.api.nvidia.com/v1",
                    api_key=nvidia_api_key
                )
                
                prompt = f"""You are a Senior Equity Analyst at a top institutional investment bank providing personalized insights for a specific investor.

STOCK: {company_name} ({ticker})

CURRENT STOCK METRICS:
- Price: ₹{current_price:.2f} ({daily_change:+.2f}% today)
- 20-Day MA: ₹{ma_20:.2f} | 50-Day MA: ₹{ma_50:.2f}
- RSI (14): {rsi:.1f} ({rsi_signal})
- Volatility: {volatility_30d:.1f}% annualized
- Market Cap: {format_market_cap(market_cap)}
- P/E Ratio: {pe_ratio:.1f}x | Forward P/E: {forward_pe:.1f}x
- P/B Ratio: {info.get('priceToBook', 0):.1f}x
- Dividend Yield: {dividend_yield:.1f}%
- Beta: {beta:.2f} (vs NIFTY)
- ROE: {roe:.1f}%
- Debt/Equity: {debt_to_equity:.1f}
- Sector: {sector}
- Industry: {industry}
{portfolio_context_str}

Provide your analysis in this exact format:

**BULL CASE** (What supports buying):
- Key positive catalysts (2-3 points)
- Why the current trend may continue
- Target upside potential

**BEAR CASE** (What supports selling/avoiding):
- Key risks and concerns (2-3 points)
- Why the current trend may reverse
- Downside risk

**PORTFOLIO FIT ANALYSIS**:
- Diversification impact: [How this affects portfolio risk]
- Suggested position size: [% based on their profile]
- Correlation warning: [If overlaps with existing holdings]

**INSTITUTIONAL VERDICT**: [Buy/Downside/Neutral with 1-sentence rationale specific to this investor]

Keep it concise, professional, and institutional-grade. No fluff. Personalize for their portfolio situation."""

                response = client.chat.completions.create(
                    model="meta/llama-3.1-405b-instruct",
                    messages=[
                        {"role": "system", "content": "You are a Senior Equity Analyst."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=1200
                )
                ai_analysis = response.choices[0].message.content
                
                base_context = {
                    "company_name": company_name,
                    "sector": sector,
                    "industry": industry,
                    "price": {
                        "current": round(current_price, 2),
                        "daily_change": round(daily_change, 2),
                        "ma_20": round(ma_20, 2),
                        "ma_50": round(ma_50, 2),
                        "high_52w": round(high_52w, 2),
                        "low_52w": round(low_52w, 2),
                        "pct_from_high": round(pct_from_high, 2),
                    },
                    "technicals": {
                        "rsi": round(rsi, 1),
                        "rsi_signal": rsi_signal,
                        "volatility_30d": round(volatility_30d, 1),
                        "trend": trend,
                        "volume_ratio": round(volume_ratio, 2),
                    },
                    "fundamentals": {
                        "market_cap": market_cap,
                        "pe_ratio": round(pe_ratio, 1) if pe_ratio else 0,
                        "forward_pe": round(forward_pe, 1) if forward_pe else 0,
                        "dividend_yield": round(dividend_yield, 2),
                        "beta": round(beta, 2),
                        "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else 0,
                        "roe": round(roe, 1) if roe else 0,
                    },
                    "portfolio_context": portfolio_context,
                }
                db.save_stock_analysis_cache(user_id, ticker, ai_analysis, base_context)
                
        except Exception as e:
            print(f"AI Analysis error: {e}")
        
        return {
            "ticker": ticker,
            "company_name": company_name,
            "sector": sector,
            "industry": industry,
            "price": {
                "current": round(current_price, 2),
                "daily_change": round(daily_change, 2),
                "ma_20": round(ma_20, 2),
                "ma_50": round(ma_50, 2),
                "high_52w": round(high_52w, 2),
                "low_52w": round(low_52w, 2),
                "pct_from_high": round(pct_from_high, 2),
            },
            "technicals": {
                "rsi": round(rsi, 1),
                "rsi_signal": rsi_signal,
                "volatility_30d": round(volatility_30d, 1),
                "trend": trend,
                "volume_ratio": round(volume_ratio, 2),
            },
            "fundamentals": {
                "market_cap": market_cap,
                "pe_ratio": round(pe_ratio, 1) if pe_ratio else 0,
                "forward_pe": round(forward_pe, 1) if forward_pe else 0,
                "dividend_yield": round(dividend_yield, 2),
                "beta": round(beta, 2),
                "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else 0,
                "roe": round(roe, 1) if roe else 0,
            },
            "ai_analysis": ai_analysis,
            "portfolio_context": portfolio_context,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "from_cache": False,
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

@app.get("/market/stock/{ticker}/analyze/progressive")
async def analyze_stock_progressive(ticker: str, user_id: str = None):
    import yfinance as yf
    import numpy as np
    from datetime import datetime, timedelta
    import json
    
    if not user_id:
        user_id = "demo"
    
    async def event_generator():
        _ticker = ticker.upper().strip()
        uid = user_id
        
        def send_event(event_type, data):
            return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        
        try:
            cached = db.get_cached_stock_analysis(uid, _ticker)
            if cached:
                cached_ai = cached["ai_analysis"]
                if isinstance(cached_ai, str):
                    try:
                        cached_ai = json.loads(cached_ai)
                    except:
                        pass
                yield send_event("complete", {
                    "ticker": _ticker,
                    "company_name": cached.get("personalized_context", {}).get("company_name", _ticker),
                    "sector": cached.get("personalized_context", {}).get("sector", "Unknown"),
                    "industry": cached.get("personalized_context", {}).get("industry", "Unknown"),
                    "price": cached.get("personalized_context", {}).get("price", {}),
                    "technicals": cached.get("personalized_context", {}).get("technicals", {}),
                    "fundamentals": cached.get("personalized_context", {}).get("fundamentals", {}),
                    "ai_analysis": cached_ai,
                    "portfolio_context": cached.get("personalized_context", {}).get("portfolio_context"),
                    "generated_at": cached["generated_at"],
                    "from_cache": True,
                })
                return
            
            yield send_event("progress", {"step": 1, "total": 5, "message": "Fetching stock data..."})
            
            end_date = datetime.today()
            start_date_60d = end_date - timedelta(days=60)
            start_date_90d = end_date - timedelta(days=90)
            
            stock = yf.Ticker(_ticker)
            hist_60d = stock.history(start=start_date_60d.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            hist_90d = stock.history(start=start_date_90d.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            
            if hist_60d.empty or "Close" not in hist_60d.columns:
                yield send_event("sse_error", {"message": f"No data available for ticker: {_ticker}"})
                return
            
            closes = hist_60d["Close"].dropna()
            volumes = hist_60d["Volume"].dropna()
            highs = hist_60d["High"]
            lows = hist_60d["Low"]
            
            current_price = float(closes.iloc[-1])
            prev_price = float(closes.iloc[-2]) if len(closes) > 1 else current_price
            daily_change = ((current_price / prev_price) - 1) * 100
            
            ma_20 = float(closes.tail(20).mean())
            ma_50 = float(closes.tail(50).mean()) if len(closes) >= 50 else ma_20
            
            delta = closes.diff()
            gain = delta.where(delta > 0, 0)
            loss = (-delta).where(delta < 0, 0)
            avg_gain = gain.tail(14).mean()
            avg_loss = loss.tail(14).mean()
            rs = avg_gain / avg_loss if avg_loss > 0 else 100
            rsi = 100 - (100 / (1 + rs))
            
            returns_30d = closes.pct_change().tail(30)
            volatility_30d = float(returns_30d.std() * np.sqrt(252) * 100)
            
            high_52w = float(highs.max()) if not highs.empty else current_price * 1.3
            low_52w = float(lows.min()) if not lows.empty else current_price * 0.7
            pct_from_high = ((high_52w - current_price) / high_52w) * 100
            
            avg_volume_20d = float(volumes.tail(20).mean()) if len(volumes) >= 20 else float(volumes.mean())
            current_volume = float(volumes.iloc[-1]) if len(volumes) > 0 else 0
            volume_ratio = current_volume / avg_volume_20d if avg_volume_20d > 0 else 1
            
            trend = "Bullish" if current_price > ma_20 > ma_50 else "Bearish" if current_price < ma_20 < ma_50 else "Neutral"
            
            if rsi > 70:
                rsi_signal = "Overbought"
            elif rsi < 30:
                rsi_signal = "Oversold"
            else:
                rsi_signal = "Neutral"
            
            yield send_event("progress", {"step": 2, "total": 5, "message": "Loading fundamentals..."})
            
            try:
                info = stock.info
                market_cap = info.get("marketCap", 0)
                pe_ratio = info.get("trailingPE", 0)
                forward_pe = info.get("forwardPE", 0)
                dividend_yield = info.get("dividendYield", 0) * 100 if info.get("dividendYield") else 0
                beta = info.get("beta", 1)
                debt_to_equity = info.get("debtToEquity", 0)
                roe = info.get("returnOnEquity", 0) * 100 if info.get("returnOnEquity") else 0
                sector = info.get("sector", "Unknown")
                industry = info.get("industry", "Unknown")
                company_name = info.get("shortName", _ticker)
            except:
                market_cap = 0
                pe_ratio = 0
                forward_pe = 0
                dividend_yield = 0
                beta = 1
                debt_to_equity = 0
                roe = 0
                sector = "Unknown"
                industry = "Unknown"
                company_name = _ticker
            
            yield send_event("progress", {"step": 3, "total": 5, "message": "Analyzing portfolio impact..."})
            
            portfolio = db.get_portfolio(uid)
            risk_profile = db.get_risk_profile(uid)
            
            portfolio_context = None
            if portfolio:
                portfolio_sectors = {}
                portfolio_tickers = []
                total_value = 0
                
                batch_tickers = [h["ticker"] for h in portfolio]
                prices = db.get_portfolio_prices_batch(batch_tickers)
                
                for h in portfolio:
                    h_price = prices.get(h["ticker"]) or h["avg_price"]
                    value = h["quantity"] * h_price
                    total_value += value
                    portfolio_sectors[h["sector"]] = portfolio_sectors.get(h["sector"], 0) + value
                    portfolio_tickers.append(h["ticker"])
                
                sector_allocation = {k: round(v/total_value*100, 1) for k, v in portfolio_sectors.items()}
                same_sector_value = portfolio_sectors.get(sector, 0)
                same_sector_pct = round(same_sector_value/total_value*100, 1) if total_value > 0 else 0
                
                portfolio_context = {
                    "holdings_count": len(portfolio),
                    "total_value": round(total_value, 2),
                    "sector_allocation": sector_allocation,
                    "existing_tickers": portfolio_tickers,
                    "current_sector_exposure_pct": same_sector_pct,
                    "sector": sector,
                }
            
            risk_tolerance = risk_profile.get("risk_tolerance", "moderate") if risk_profile else "moderate"
            investment_horizon = risk_profile.get("investment_horizon", "medium") if risk_profile else "medium"
            portfolio_size = risk_profile.get("portfolio_size", "medium") if risk_profile else "medium"
            
            yield send_event("progress", {"step": 4, "total": 5, "message": "Generating AI insights..."})
            
            def format_inr(value):
                if value >= 10000000:
                    return f"₹{value/10000000:.1f}Cr"
                elif value >= 100000:
                    return f"₹{value/100000:.1f}L"
                elif value >= 1000:
                    return f"₹{value/1000:.1f}K"
                return f"₹{value:.0f}"
            
            def format_market_cap(value):
                if value >= 10000000:
                    return f"₹{value/10000000:.0f}Cr"
                elif value >= 100000:
                    return f"₹{value/100000:.0f}L"
                return f"₹{value:.0f}"
            
            portfolio_context_str = ""
            if portfolio_context:
                portfolio_context_str = f"""
INVESTOR PORTFOLIO CONTEXT:
- Risk Profile: {risk_tolerance.upper()} risk tolerance | {investment_horizon.upper()} investment horizon
- Portfolio Size: {portfolio_size}
- Current Holdings: {portfolio_context['holdings_count']} stocks worth {format_inr(portfolio_context['total_value'])}
- Sector Allocation: {', '.join([f"{k}: {v}%" for k, v in portfolio_context['sector_allocation'].items()])}
- Existing Exposure to {sector}: {portfolio_context['current_sector_exposure_pct']}%
- Existing Holdings: {', '.join(portfolio_context['existing_tickers'])}

ANALYSIS REQUIREMENTS:
1. FLAG if this stock would create >25% sector concentration
2. SUGGEST position size based on portfolio size (small: 2-5%, medium: 3-7%, large: 5-10%)
3. ASSESS correlation with existing holdings
4. RECOMMEND if it improves portfolio diversification
"""
            
            ai_analysis = None
            try:
                from openai import OpenAI
                import os
                from dotenv import load_dotenv
                load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
                nvidia_api_key = os.getenv("NVIDIA_API_KEY")
                if nvidia_api_key:
                    client = OpenAI(
                        base_url="https://integrate.api.nvidia.com/v1",
                        api_key=nvidia_api_key
                    )
                    
                    prompt = f"""You are a Senior Equity Analyst providing structured stock analysis. ALWAYS respond with valid JSON only - no markdown, no text outside the JSON.

STOCK: {company_name} ({_ticker})

METRICS:
- Price: ₹{current_price:.2f} ({daily_change:+.2f}% today)
- RSI: {rsi:.1f} ({rsi_signal})
- MA-20: ₹{ma_20:.2f}, MA-50: ₹{ma_50:.2f}
- P/E: {pe_ratio:.1f}x, Forward P/E: {forward_pe:.1f}x
- ROE: {roe:.1f}%, Debt/Equity: {debt_to_equity:.1f}
- Beta: {beta:.2f}, Market Cap: {format_market_cap(market_cap)}
- Sector: {sector}
{portfolio_context_str}

Output JSON strictly matching this schema:
{{
    "metric_insights": {{
        "rsi": "string (1 sentence: what RSI value means for this stock)",
        "moving_averages": "string (1 sentence: price vs MAs, trend direction)",
        "valuation": "string (1 sentence: P/E assessment)",
        "profitability": "string (1 sentence: ROE strength)",
        "leverage": "string (1 sentence: debt sustainability)",
        "market_sensitivity": "string (1 sentence: beta interpretation)"
    }},
    "bull_case": {{
        "catalysts": ["string", "string", "string"],
        "trend_continuation": "string (1 sentence)",
        "upside_potential": "string (1 sentence)"
    }},
    "bear_case": {{
        "risks": ["string", "string", "string"],
        "trend_reversal": "string (1 sentence)",
        "downside_risk": "string (1 sentence)"
    }},
    "portfolio_fit": {{
        "diversification": "string (1 sentence)",
        "suggested_size": "string (e.g., '3-5% of portfolio')",
        "correlation_warning": "string (1 sentence)"
    }},
    "verdict": {{
        "recommendation": "BUY|BEARISH|NEUTRAL",
        "rationale": "string (1 sentence)"
    }},
    "confidence_score": 0.85
}}

Rules:
- Use exactly these field names
- Keep each string under 30 words
- catalysts and risks arrays must have exactly 3 items
- recommendation must be exactly: BUY, BEARISH, or NEUTRAL
- confidence_score between 0.0 and 1.0
- Output valid JSON only - no markdown code blocks"""
                    
                    response = client.chat.completions.create(
                        model="meta/llama-3.1-405b-instruct",
                        messages=[
                            {"role": "system", "content": "You are a Senior Equity Analyst. Always respond with valid JSON only."},
                            {"role": "user", "content": prompt}
                        ],
                        temperature=0.1,
                        max_tokens=1500,
                        seed=42
                    )
                    raw_response = response.choices[0].message.content
                    try:
                        ai_analysis_json = json.loads(raw_response)
                        ai_analysis = json.dumps(ai_analysis_json)
                    except:
                        ai_analysis_json = {
                            "metric_insights": {"rsi": "Unable to parse", "moving_averages": "", "valuation": "", "profitability": "", "leverage": "", "market_sensitivity": ""},
                            "bull_case": {"catalysts": ["N/A"], "trend_continuation": "N/A", "upside_potential": "N/A"},
                            "bear_case": {"risks": ["N/A"], "trend_reversal": "N/A", "downside_risk": "N/A"},
                            "portfolio_fit": {"diversification": "N/A", "suggested_size": "N/A", "correlation_warning": "N/A"},
                            "verdict": {"recommendation": "NEUTRAL", "rationale": "Analysis unavailable"},
                            "confidence_score": 0.0
                        }
                        ai_analysis = json.dumps(ai_analysis_json)
                    
                    base_context = {
                        "company_name": company_name,
                        "sector": sector,
                        "industry": industry,
                        "price": {
                            "current": round(current_price, 2),
                            "daily_change": round(daily_change, 2),
                            "ma_20": round(ma_20, 2),
                            "ma_50": round(ma_50, 2),
                            "high_52w": round(high_52w, 2),
                            "low_52w": round(low_52w, 2),
                            "pct_from_high": round(pct_from_high, 2),
                        },
                        "technicals": {
                            "rsi": round(rsi, 1),
                            "rsi_signal": rsi_signal,
                            "volatility_30d": round(volatility_30d, 1),
                            "trend": trend,
                            "volume_ratio": round(volume_ratio, 2),
                        },
                        "fundamentals": {
                            "market_cap": market_cap,
                            "pe_ratio": round(pe_ratio, 1) if pe_ratio else 0,
                            "forward_pe": round(forward_pe, 1) if forward_pe else 0,
                            "dividend_yield": round(dividend_yield, 2),
                            "beta": round(beta, 2),
                            "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else 0,
                            "roe": round(roe, 1) if roe else 0,
                        },
                        "portfolio_context": portfolio_context,
                    }
                    db.save_stock_analysis_cache(uid, _ticker, ai_analysis, base_context)
                    
            except Exception as e:
                print(f"AI Analysis error: {e}")
                ai_analysis_json = None
            
            yield send_event("progress", {"step": 5, "total": 5, "message": "Finalizing..."})
            
            yield send_event("complete", {
                "ticker": _ticker,
                "company_name": company_name,
                "sector": sector,
                "industry": industry,
                "price": {
                    "current": round(current_price, 2),
                    "daily_change": round(daily_change, 2),
                    "ma_20": round(ma_20, 2),
                    "ma_50": round(ma_50, 2),
                    "high_52w": round(high_52w, 2),
                    "low_52w": round(low_52w, 2),
                    "pct_from_high": round(pct_from_high, 2),
                },
                "technicals": {
                    "rsi": round(rsi, 1),
                    "rsi_signal": rsi_signal,
                    "volatility_30d": round(volatility_30d, 1),
                    "trend": trend,
                    "volume_ratio": round(volume_ratio, 2),
                },
                "fundamentals": {
                    "market_cap": market_cap,
                    "pe_ratio": round(pe_ratio, 1) if pe_ratio else 0,
                    "forward_pe": round(forward_pe, 1) if forward_pe else 0,
                    "dividend_yield": round(dividend_yield, 2),
                    "beta": round(beta, 2),
                    "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else 0,
                    "roe": round(roe, 1) if roe else 0,
                },
                "ai_analysis": ai_analysis_json,
                "portfolio_context": portfolio_context,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "from_cache": False,
            })
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield send_event("sse_error", {"message": str(e)})
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
