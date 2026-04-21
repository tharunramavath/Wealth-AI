"""
Stock Data Fetching with Cache
- Fetches price history from yfinance
- Caches data for 24 hours to reduce API calls
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from backend import database as db

CACHE_TTL_HOURS = 24


def get_stock_price_history(ticker: str, days: int = 365) -> list:
    ticker = ticker.upper()
    cached_data = db.get_cached_price_history(ticker, days)
    
    if cached_data and len(cached_data) >= min(30, days // 2):
        return cached_data
    
    fresh_data = _fetch_from_yfinance(ticker, days)
    
    if fresh_data and len(fresh_data) >= 30:
        db.cache_price_history(ticker, fresh_data)
    
    return fresh_data


def _fetch_from_yfinance(ticker: str, days: int = 365) -> list:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{days}d")
        
        if hist.empty:
            return []
        
        data = []
        for date, row in hist.iterrows():
            data.append({
                "date": date.strftime("%Y-%m-%d"),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"])
            })
        
        return data
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return []
