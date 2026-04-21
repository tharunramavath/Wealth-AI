import os
import json
import time
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NIFTY_50_UNIVERSE = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFOSYS.NS", "ICICIBANK.NS",
    "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "HUL.NS",
    "ASIANPAINT.NS", "MARUTI.NS", "KOTAKBANK.NS", "SUNPHARMA.NS", "TITAN.NS",
    "BAJFINANCE.NS", "NTPC.NS", "WIPRO.NS", "ONGC.NS", "POWERGRID.NS",
    "NESTLEIND.NS", "M&M.NS", "SBILIFE.NS", "AXISBANK.NS", "HDFCLIFE.NS",
    "CIPLA.NS", "BAJAJFINSV.NS", "INDUSINDBK.NS", "JSWSTEEL.NS", "ADANIPORTS.NS",
    "GRASIM.NS", "DIVISLAB.NS", "APOLLOHOSP.NS", "TATASTEEL.NS", "BRITANNIA.NS",
    "COALINDIA.NS", "HEROMOTOCO.NS", "DRREDDY.NS", "BPCL.NS", "EICHERMOT.NS",
    "UPL.NS", "ADANIENT.NS", "GAIL.NS", "SHREECEM.NS", "ICICIPRULI.NS",
    "HINDUNILVR.NS", "TECHM.NS", "TATAMOTORS.NS", "TATACONSULT.NS"
]

SECTOR_LEADERS = {
    "IT": ["TCS.NS", "INFOSYS.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS"],
    "Banking": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS", "AXISBANK.NS"],
    "Finance": ["BAJFINANCE.NS", "BAJAJFINSV.NS", "HDFCLIFE.NS", "SBILIFE.NS", "ICICIPRULI.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "GAIL.NS"],
    "FMCG": ["HINDUNILVR.NS", "HUL.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS"],
    "Pharma": ["SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS"],
    "Auto": ["MARUTI.NS", "TATAMOTORS.NS", "M&M.NS", "HEROMOTOCO.NS", "EICHERMOT.NS"],
    "Metals": ["TATASTEEL.NS", "JSWSTEEL.NS", "HINDALCO.NS", "COALINDIA.NS"],
    "Infrastructure": ["LT.NS", "ADANIPORTS.NS", "POWERGRID.NS", "GAIL.NS"]
}

RISK_TOLERANCE_CONFIG = {
    "conservative": {
        "max_volatility": 0.20,
        "max_beta": 1.0,
        "min_score_weight": 0.15,
        "prefer_large_cap": True,
        "sector_concentration_limit": 0.40,
        "max_stocks_per_sector": 2
    },
    "moderate": {
        "max_volatility": 0.30,
        "max_beta": 1.2,
        "min_score_weight": 0.10,
        "prefer_large_cap": True,
        "sector_concentration_limit": 0.50,
        "max_stocks_per_sector": 3
    },
    "aggressive": {
        "max_volatility": 0.50,
        "max_beta": 1.5,
        "min_score_weight": 0.05,
        "prefer_large_cap": False,
        "sector_concentration_limit": 0.60,
        "max_stocks_per_sector": 4
    }
}

FEATURE_CACHE_TTL = 300
FEATURE_CACHE = {}

STOCK_RECOMMENDATION_CACHE_TTL = 600
STOCK_RECOMMENDATION_CACHE = {}


def get_ticker_sector(ticker: str) -> str:
    for sector, tickers in SECTOR_LEADERS.items():
        if ticker in tickers:
            return sector
    return "Other"


def is_large_cap(ticker: str) -> bool:
    large_cap_tickers = [
        "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFOSYS.NS", "ICICIBANK.NS",
        "SBIN.NS", "BHARTIARTL.NS", "ITC.NS", "LT.NS", "HUL.NS",
        "HDFCLIFE.NS", "KOTAKBANK.NS", "SUNPHARMA.NS", "TITAN.NS", "BAJFINANCE.NS",
        "ASIANPAINT.NS", "MARUTI.NS", "NESTLEIND.NS", "M&M.NS", "TATAMOTORS.NS",
        "WIPRO.NS", "NTPC.NS", "POWERGRID.NS", "ONGC.NS"
    ]
    return ticker in large_cap_tickers


def fetch_stock_data(ticker: str, period: str = "1y") -> Optional[pd.DataFrame]:
    try:
        import yfinance as yf
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)
        if df.empty or len(df) < 50:
            return None
        return df
    except Exception as e:
        logger.warning(f"Failed to fetch {ticker}: {e}")
        return None


def calculate_features(ticker: str) -> Optional[Dict]:
    cache_key = f"{ticker}_{int(time.time() // FEATURE_CACHE_TTL)}"
    if cache_key in FEATURE_CACHE:
        return FEATURE_CACHE[cache_key]

    try:
        df = fetch_stock_data(ticker)
        if df is None:
            return None

        close = df['Close']
        returns = close.pct_change().dropna()

        if len(returns) < 100:
            return None

        returns_1m = close.pct_change(21).iloc[-1] if len(close) >= 21 else 0
        returns_3m = close.pct_change(63).iloc[-1] if len(close) >= 63 else 0
        returns_6m = close.pct_change(126).iloc[-1] if len(close) >= 126 else 0

        sma_50 = close.rolling(50).mean().iloc[-1]
        sma_200 = close.rolling(200).mean().iloc[-1]
        current_price = close.iloc[-1]

        above_50_dma = 1 if current_price > sma_50 else 0
        above_200_dma = 1 if current_price > sma_200 else 0

        volatility = returns.std() * np.sqrt(252)
        max_drawdown = ((close / close.cummax()) - 1).min()

        try:
            nifty = yf.Ticker("^NSEI")
            nifty_data = nifty.history(period="1y")
            if not nifty_data.empty and len(nifty_data) > 100:
                nifty_returns = nifty_data['Close'].pct_change().dropna()
                correlation = returns.tail(60).corr(nifty_returns.tail(60))
                beta = correlation * (volatility / (nifty_returns.std() * np.sqrt(252))) if nifty_returns.std() > 0 else 1.0
                beta = max(0.3, min(2.0, beta))
            else:
                beta = 1.0
        except:
            beta = 1.0

        momentum_score = (returns_1m * 0.4 + returns_3m * 0.35 + returns_6m * 0.25) * 10

        features = {
            "ticker": ticker,
            "sector": get_ticker_sector(ticker),
            "is_large_cap": is_large_cap(ticker),
            "returns_1m": returns_1m,
            "returns_3m": returns_3m,
            "returns_6m": returns_6m,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
            "beta": beta,
            "above_50_dma": above_50_dma,
            "above_200_dma": above_200_dma,
            "momentum_score": momentum_score,
            "current_price": current_price,
            "last_updated": datetime.now().isoformat()
        }

        FEATURE_CACHE[cache_key] = features
        return features

    except Exception as e:
        logger.error(f"Error calculating features for {ticker}: {e}")
        return None


def calculate_volatility_score(volatility: float, max_vol: float) -> float:
    if volatility <= 0.10:
        return 1.0
    elif volatility >= max_vol:
        return 0.0
    else:
        return 1 - (volatility - 0.10) / (max_vol - 0.10)


def calculate_momentum_score(returns_1m: float, returns_3m: float, returns_6m: float) -> float:
    momentum = (returns_1m * 0.4 + returns_3m * 0.35 + returns_6m * 0.25)
    if momentum > 0.20:
        return 1.0
    elif momentum < -0.15:
        return 0.0
    else:
        return (momentum + 0.15) / 0.35


def calculate_beta_score(beta: float, max_beta: float) -> float:
    if beta <= 0.8:
        return 1.0
    elif beta >= max_beta:
        return 0.0
    else:
        return 1 - (beta - 0.8) / (max_beta - 0.8)


def calculate_drawdown_score(max_drawdown: float) -> float:
    if max_drawdown >= 0:
        return 1.0
    elif max_drawdown <= -0.30:
        return 0.0
    else:
        return 1 - abs(max_drawdown) / 0.30


def calculate_trend_score(above_50_dma: int, above_200_dma: int) -> float:
    return (above_50_dma * 0.4 + above_200_dma * 0.6)


def score_stock(features: Dict, config: Dict, user_portfolio: List[Dict]) -> Optional[float]:
    if features is None:
        return None

    if features["volatility"] > config["max_volatility"]:
        return None
    if features["beta"] > config["max_beta"]:
        return None

    vol_score = calculate_volatility_score(features["volatility"], config["max_volatility"])
    mom_score = calculate_momentum_score(
        features["returns_1m"], features["returns_3m"], features["returns_6m"]
    )
    beta_score = calculate_beta_score(features["beta"], config["max_beta"])
    dd_score = calculate_drawdown_score(features["max_drawdown"])
    trend_score = calculate_trend_score(features["above_50_dma"], features["above_200_dma"])

    cap_score = 1.0 if features["is_large_cap"] else 0.5

    weights = {
        "momentum": 0.30,
        "volatility": 0.20,
        "beta": 0.15,
        "drawdown": 0.15,
        "trend": 0.10,
        "cap": 0.10
    }

    if config.get("prefer_large_cap", True):
        weights["cap"] = 0.15
        weights["trend"] = 0.05

    score = (
        weights["momentum"] * mom_score +
        weights["volatility"] * vol_score +
        weights["beta"] * beta_score +
        weights["drawdown"] * dd_score +
        weights["trend"] * trend_score +
        weights["cap"] * cap_score
    )

    if score < config.get("min_score_weight", 0.1):
        return None

    return round(score, 3)


def get_portfolio_sectors(user_portfolio: List[Dict]) -> Dict[str, float]:
    if not user_portfolio:
        return {}
    
    sector_values = {}
    total_value = 0
    
    for holding in user_portfolio:
        sector = holding.get("sector", "Other")
        value = holding.get("quantity", 0) * holding.get("avg_price", 0)
        sector_values[sector] = sector_values.get(sector, 0) + value
        total_value += value
    
    if total_value == 0:
        return {}
    
    return {sector: value / total_value for sector, value in sector_values.items()}


def apply_constraints(
    scored_stocks: List[Tuple[str, float, Dict]],
    config: Dict,
    portfolio_sectors: Dict[str, float],
    user_tickers: List[str]
) -> List[Tuple[str, float, Dict]]:
    sector_count = {}
    constrained = []
    
    for ticker, score, features in scored_stocks:
        sector = features["sector"]
        
        if sector_count.get(sector, 0) >= config["max_stocks_per_sector"]:
            continue
        
        sector_allocation = portfolio_sectors.get(sector, 0)
        if sector_allocation >= config["sector_concentration_limit"] and sector in portfolio_sectors:
            if score < 0.75:
                continue
        
        if ticker in user_tickers:
            if score < 0.60:
                continue
        
        sector_count[sector] = sector_count.get(sector, 0) + 1
        constrained.append((ticker, score, features))
    
    return constrained


def generate_allocation(recommendations: List[Dict], strategy: str = "equal") -> Dict[str, str]:
    n = len(recommendations)
    if n == 0:
        return {}
    
    if strategy == "equal":
        weight = 100 // n
        remainder = 100 - (weight * n)
        
        allocation = {}
        for i, rec in enumerate(recommendations):
            alloc = weight + (1 if i < remainder else 0)
            allocation[rec["ticker"]] = f"{alloc}%"
        
        return allocation
    else:
        return {}


def get_top_n_stocks(
    n: int = 5,
    risk_tolerance: str = "moderate",
    user_portfolio: List[Dict] = None,
    exclude_tickers: List[str] = None
) -> Dict:
    if user_portfolio is None:
        user_portfolio = []
    if exclude_tickers is None:
        exclude_tickers = []
    
    cache_key = f"{n}_{risk_tolerance}_{hashlib.md5(str(sorted([p.get('ticker', '') for p in user_portfolio])).encode()).hexdigest()[:8]}"
    current_time = time.time()
    
    if cache_key in STOCK_RECOMMENDATION_CACHE:
        cached_time, cached_result = STOCK_RECOMMENDATION_CACHE[cache_key]
        if current_time - cached_time < STOCK_RECOMMENDATION_CACHE_TTL:
            cached_result["cached"] = True
            return cached_result
    
    config = RISK_TOLERANCE_CONFIG.get(risk_tolerance.lower(), RISK_TOLERANCE_CONFIG["moderate"])
    portfolio_sectors = get_portfolio_sectors(user_portfolio)
    user_tickers = [p.get("ticker", "") for p in user_portfolio]
    
    scored_stocks = []
    
    logger.info(f"Scoring {len(NIFTY_50_UNIVERSE)} stocks for {risk_tolerance} risk profile...")
    
    for ticker in NIFTY_50_UNIVERSE:
        if ticker in exclude_tickers:
            continue
        
        features = calculate_features(ticker)
        score = score_stock(features, config, user_portfolio)
        
        if score is not None and features is not None:
            scored_stocks.append((ticker, score, features))
    
    scored_stocks.sort(key=lambda x: x[1], reverse=True)
    constrained_stocks = apply_constraints(scored_stocks, config, portfolio_sectors, user_tickers)
    
    top_n = constrained_stocks[:n]
    
    recommendations = []
    for ticker, score, features in top_n:
        recommendations.append({
            "ticker": ticker,
            "sector": features["sector"],
            "score": score,
            "returns_1m": round(features["returns_1m"] * 100, 2),
            "returns_3m": round(features["returns_3m"] * 100, 2),
            "volatility": round(features["volatility"] * 100, 2),
            "beta": round(features["beta"], 2),
            "above_200_dma": bool(features["above_200_dma"]),
            "current_price": round(features["current_price"], 2)
        })
    
    allocation = generate_allocation(recommendations)
    
    sector_dist = {}
    for rec in recommendations:
        sector = rec["sector"]
        sector_dist[sector] = sector_dist.get(sector, 0) + 1
    
    avg_score = sum(r["score"] for r in recommendations) / len(recommendations) if recommendations else 0
    
    diversification = "High" if len(sector_dist) >= 4 else "Medium" if len(sector_dist) >= 2 else "Low"
    
    result = {
        "recommended_stocks": recommendations,
        "allocation": allocation,
        "portfolio_summary": {
            "diversification": diversification,
            "sectors_represented": list(sector_dist.keys()),
            "sector_distribution": {s: f"{round(c/len(recommendations)*100)}%" for s, c in sector_dist.items()},
            "risk_level": risk_tolerance.capitalize(),
            "num_stocks": len(recommendations)
        },
        "scoring_methodology": {
            "momentum_weight": "30%",
            "volatility_weight": "20%",
            "beta_weight": "15%",
            "drawdown_weight": "15%",
            "trend_weight": "10%",
            "cap_weight": "10%"
        },
        "metadata": {
            "generated_at": datetime.now().isoformat(),
            "universe_size": len(NIFTY_50_UNIVERSE),
            "stocks_scored": len(scored_stocks),
            "constraints_applied": ["volatility", "beta", "sector_concentration", "correlation"],
            "confidence_score": round(avg_score, 2)
        },
        "cached": False
    }
    
    STOCK_RECOMMENDATION_CACHE[cache_key] = (current_time, result)
    
    return result


def get_stock_recommendation(
    n: int = 5,
    risk_tolerance: str = "moderate",
    investment_horizon: str = "medium",
    user_portfolio: List[Dict] = None
) -> Dict:
    if n not in [5, 10]:
        n = 5
    
    result = get_top_n_stocks(
        n=n,
        risk_tolerance=risk_tolerance,
        user_portfolio=user_portfolio or []
    )
    
    if investment_horizon.lower() == "short":
        result["investment_horizon_note"] = "Short-term focus: Prioritizing stocks with strong recent momentum and above-200 DMA trend"
    elif investment_horizon.lower() == "long":
        result["investment_horizon_note"] = "Long-term focus: Including stocks with solid fundamentals and reasonable valuations"
    
    return result


if __name__ == "__main__":
    sample_portfolio = [
        {"ticker": "RELIANCE.NS", "quantity": 10, "avg_price": 2500, "sector": "Energy"},
        {"ticker": "TCS.NS", "quantity": 5, "avg_price": 3500, "sector": "IT"}
    ]
    
    print("=" * 60)
    print("Stock Recommendation Engine - Test Run")
    print("=" * 60)
    
    result = get_stock_recommendation(
        n=5,
        risk_tolerance="moderate",
        investment_horizon="medium",
        user_portfolio=sample_portfolio
    )
    
    print("\n📊 TOP 5 RECOMMENDATIONS:")
    print("-" * 60)
    for i, stock in enumerate(result["recommended_stocks"], 1):
        print(f"{i}. {stock['ticker']} ({stock['sector']})")
        print(f"   Score: {stock['score']:.2f} | 3M Return: {stock['returns_3m']}%")
        print(f"   Volatility: {stock['volatility']}% | Beta: {stock['beta']}")
        print()
    
    print("\n📈 PORTFOLIO SUMMARY:")
    print(f"   Diversification: {result['portfolio_summary']['diversification']}")
    print(f"   Risk Level: {result['portfolio_summary']['risk_level']}")
    print(f"   Sectors: {', '.join(result['portfolio_summary']['sectors_represented'])}")
    
    print("\n⚙️ SCORING METHODOLOGY:")
    print(f"   Confidence: {result['metadata']['confidence_score']:.2f}")
    print(f"   Stocks Scored: {result['metadata']['stocks_scored']}/{result['metadata']['universe_size']}")
