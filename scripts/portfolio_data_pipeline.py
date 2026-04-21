"""
Portfolio Historical Data Pipeline
Fetches 1 year of OHLCV data for user's portfolio holdings and stores in database.
Run daily via cron or manually.
"""

import sys
import os
from datetime import datetime, timedelta
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import yfinance as yf
import pandas as pd
from tqdm import tqdm

from backend.database import (
    save_batch_price_history,
    get_portfolio,
    get_latest_price_date,
    init_db
)

DAYS_HISTORY = 365
BATCH_SIZE = 5
REQUEST_DELAY = 0.5

def get_date_range():
    end_date = datetime.today()
    start_date = end_date - timedelta(days=DAYS_HISTORY)
    return start_date, end_date

def fetch_ticker_history(ticker, start_date, end_date, max_retries=3):
    for attempt in range(max_retries):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            
            if hist.empty:
                return []
            
            data = []
            for date, row in hist.iterrows():
                date_str = date.strftime("%Y-%m-%d")
                data.append({
                    'date': date_str,
                    'open': float(row['Open']),
                    'high': float(row['High']),
                    'low': float(row['Low']),
                    'close': float(row['Close']),
                    'volume': int(row['Volume'])
                })
            return data
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(REQUEST_DELAY * (attempt + 1))
            else:
                print(f"  Failed to fetch {ticker}: {e}")
                return []
    return []

def sync_user_portfolio(user_id, force_full_refresh=False):
    print(f"\n{'='*60}")
    print(f"Syncing portfolio for user: {user_id}")
    print(f"{'='*60}")
    
    holdings = get_portfolio(user_id)
    
    if not holdings:
        print("No holdings found in portfolio.")
        return {"tickers_processed": 0, "days_fetched": 0}
    
    tickers = [h['ticker'] for h in holdings]
    print(f"Found {len(tickers)} holdings: {', '.join(tickers)}")
    
    start_date, end_date = get_date_range()
    total_records = 0
    processed = 0
    
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i+BATCH_SIZE]
        print(f"\nBatch {i//BATCH_SIZE + 1}: Processing {batch}...")
        
        for ticker in batch:
            if not force_full_refresh:
                latest_date = get_latest_price_date(user_id, ticker)
                if latest_date:
                    from datetime import datetime as dt
                    latest_dt = dt.strptime(latest_date, "%Y-%m-%d")
                    if (datetime.today() - latest_dt).days <= 1:
                        print(f"  {ticker}: Already up to date ({latest_date})")
                        processed += 1
                        continue
            
            print(f"  Fetching {ticker} ({start_date.date()} to {end_date.date()})...", end=" ")
            data = fetch_ticker_history(ticker, start_date, end_date)
            
            if data:
                save_batch_price_history(user_id, ticker, data)
                print(f"[OK] {len(data)} records")
                total_records += len(data)
            else:
                print("[FAIL] No data")
            
            processed += 1
            time.sleep(REQUEST_DELAY)
    
    return {
        "tickers_processed": processed,
        "days_fetched": DAYS_HISTORY,
        "total_records": total_records
    }

def sync_all_users():
    from backend.database import _conn
    
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT user_id FROM portfolios")
    users = [r[0] for r in c.fetchall()]
    conn.close()
    
    print(f"\nFound {len(users)} users with portfolios")
    
    results = []
    for user_id in users:
        result = sync_user_portfolio(user_id)
        results.append({"user_id": user_id, **result})
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Portfolio Historical Data Pipeline')
    parser.add_argument('--user', '-u', type=str, help='Specific user ID to sync')
    parser.add_argument('--all', '-a', action='store_true', help='Sync all users')
    parser.add_argument('--force', '-f', action='store_true', help='Force full refresh (ignore cache)')
    parser.add_argument('--ticker', '-t', type=str, help='Sync specific ticker for user')
    args = parser.parse_args()
    
    print(f"\n{'#'*60}")
    print(f"# Portfolio Historical Data Pipeline")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"# History: {DAYS_HISTORY} days")
    print(f"{'#'*60}")
    
    init_db()
    
    if args.user:
        result = sync_user_portfolio(args.user, force_full_refresh=args.force)
        print(f"\nCompleted: {result}")
    elif args.all:
        results = sync_all_users()
        print(f"\n{'='*60}")
        print("Summary:")
        for r in results:
            print(f"  {r['user_id']}: {r['tickers_processed']} tickers, {r['total_records']} records")
    elif args.ticker:
        if not args.user:
            print("Error: --user required with --ticker")
            return
        start_date, end_date = get_date_range()
        print(f"Fetching {args.ticker}...")
        data = fetch_ticker_history(args.ticker, start_date, end_date)
        if data:
            save_batch_price_history(args.user, args.ticker, data)
            print(f"Saved {len(data)} records")
        else:
            print("No data found")
    else:
        print("\nUsage:")
        print("  python portfolio_data_pipeline.py --user USER_ID           # Sync single user")
        print("  python portfolio_data_pipeline.py --all                   # Sync all users")
        print("  python portfolio_data_pipeline.py --user ID --ticker TICK # Sync specific ticker")
        print("  python portfolio_data_pipeline.py --user ID --force       # Force full refresh")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
