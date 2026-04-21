import sqlite3
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "market_data.db")

SECTOR_MAP = {
    "Technology": ["TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS"],
    "Financials": ["HDFCBANK.NS", "ICICIBANK.NS", "SBIN.NS", "KOTAKBANK.NS"],
    "Energy": ["RELIANCE.NS", "ONGC.NS", "NTPC.NS"],
    "Consumer": ["ITC.NS", "HINDUNILVR.NS", "NESTLEIND.NS"],
    "Automobile": ["TATAMOTORS.NS", "M&M.NS", "MARUTI.NS"],
    "Telecom": ["BHARTIARTL.NS"],
    "Commodity/Gold": ["GOLDBEES.NS", "SILVERBEES.NS"],
    "Broad Market/Bonds": ["NIFTYBEES.NS", "JUNIORBEES.NS", "LIQUIDBEES.NS", "Cash"]
}

def get_sector(ticker):
    for sector, tickers in SECTOR_MAP.items():
        if ticker in tickers:
            return sector
    return "Other"

def _get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            ticker TEXT PRIMARY KEY,
            sector TEXT,
            volatility REAL,
            beta REAL
        )
    ''')
    conn.commit()
    conn.close()

def update_metadata():
    init_db()
    if not os.path.exists("data/raw/prices.csv"):
        print("⚠️ Missing prices.csv. Run data pipeline first.")
        return
        
    prices = pd.read_csv("data/raw/prices.csv", index_col=0, parse_dates=True)
    returns = prices.pct_change().dropna()
    
    # Use Nifty 50 Index as the benchmark for Indian Markets
    benchmark_ticker = "^NSEI"
    if benchmark_ticker not in returns.columns:
        # Fallback to NIFTYBEES if index is missing
        benchmark_ticker = "NIFTYBEES.NS" if "NIFTYBEES.NS" in returns.columns else None
    
    benchmark_returns = returns[benchmark_ticker] if benchmark_ticker else None
    
    records = []
    for ticker in prices.columns:
        if ticker == "Cash": continue
        
        vol = returns[ticker].std() * np.sqrt(252)
        
        beta = 1.0
        if benchmark_returns is not None and ticker != benchmark_ticker:
            try:
                cov = returns[[ticker, benchmark_ticker]].cov().iloc[0, 1]
                var = benchmark_returns.var()
                beta = cov / var if var > 0 else 1.0
            except:
                beta = 1.0
            
        records.append((ticker, get_sector(ticker), round(vol, 4), round(beta, 4)))
    
    records.append(("Cash", "Cash", 0.0, 0.0))
    
    conn = _get_conn()
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR REPLACE INTO assets (ticker, sector, volatility, beta)
        VALUES (?, ?, ?, ?)
    ''', records)
    conn.commit()
    conn.close()
    print(f"✅ Sub-system: Structured DB populated with {len(records)} assets.")

def get_asset_metadata(tickers):
    conn = _get_conn()
    placeholders = ','.join('?' for _ in tickers)
    query = f"SELECT ticker, sector, volatility, beta FROM assets WHERE ticker IN ({placeholders})"
    df = pd.read_sql_query(query, conn, params=tickers)
    conn.close()
    return df

if __name__ == "__main__":
    update_metadata()
