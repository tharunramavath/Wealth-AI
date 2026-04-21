import os
import re
import json
import warnings
import pandas as pd
import numpy as np
import feedparser
import yfinance as yf
import html
from dateutil import parser as date_parser
from datetime import datetime, timedelta

warnings.filterwarnings('ignore')

DIRS = ["data/raw", "data/processed", "data/clients", "faiss_index"]
for d in DIRS:
    os.makedirs(d, exist_ok=True)

NIFTY_SECTORALS = {
    "^CNXIT": "Nifty IT",
    "^CNXBANK": "Nifty Bank",
    "^CNXAUTO": "Nifty Auto",
    "^CNXFMCG": "Nifty FMCG",
    "^CNXPHARMA": "Nifty Pharma",
    "^CNXMETAL": "Nifty Metal",
    "^CNXREALTY": "Nifty Realty",
    "^CNXENERGY": "Nifty Energy",
    "^CNXFIN SERVICE": "Nifty Financial Services",
    "^CNXCONSUM": "Nifty Consumer Durables",
    "^CNXMEDIA": "Nifty Media",
    "^CNXPSUBANK": "Nifty PSU Bank",
    "^CNXINFRA": "Nifty Infrastructure",
    "^CNXMID50": "Nifty Midcap 50",
}

SECTOR_CONSTITUENTS = {
    "^CNXIT": [
        {"ticker": "TCS.NS", "weight": 28.5, "name": "Tata Consultancy Services"},
        {"ticker": "INFY.NS", "weight": 24.3, "name": "Infosys"},
        {"ticker": "WIPRO.NS", "weight": 7.8, "name": "Wipro"},
        {"ticker": "HCLTECH.NS", "weight": 7.2, "name": "HCL Technologies"},
        {"ticker": "TECHM.NS", "weight": 5.5, "name": "Tech Mahindra"},
        {"ticker": "LTTS.NS", "weight": 3.8, "name": "L&T Technology Services"},
        {"ticker": "MPHASIS.NS", "weight": 2.9, "name": "Mphasis"},
        {"ticker": "PERSISTENT.NS", "weight": 2.5, "name": "Persistent Systems"},
    ],
    "^CNXBANK": [
        {"ticker": "HDFCBANK.NS", "weight": 26.8, "name": "HDFC Bank"},
        {"ticker": "ICICIBANK.NS", "weight": 22.5, "name": "ICICI Bank"},
        {"ticker": "SBIN.NS", "weight": 14.2, "name": "State Bank of India"},
        {"ticker": "KOTAKBANK.NS", "weight": 12.5, "name": "Kotak Mahindra Bank"},
        {"ticker": "AXISBANK.NS", "weight": 9.8, "name": "Axis Bank"},
        {"ticker": "INDUSINDBK.NS", "weight": 7.5, "name": "IndusInd Bank"},
        {"ticker": "IDFCFIRSTB.NS", "weight": 3.2, "name": "IDFC First Bank"},
        {"ticker": "BANDHANBNK.NS", "weight": 3.5, "name": "Bandhan Bank"},
    ],
    "^CNXAUTO": [
        {"ticker": "MARUTI.NS", "weight": 22.5, "name": "Maruti Suzuki"},
        {"ticker": "TATAMOTORS.NS", "weight": 18.8, "name": "Tata Motors"},
        {"ticker": "M&M.NS", "weight": 14.2, "name": "Mahindra & Mahindra"},
        {"ticker": "BAJAJ-AUTO.NS", "weight": 12.5, "name": "Bajaj Auto"},
        {"ticker": "HEROMOTOCO.NS", "weight": 8.5, "name": "Hero MotoCorp"},
        {"ticker": "EICHERMOT.NS", "weight": 7.2, "name": "Eicher Motors"},
        {"ticker": "TVSMOTOR.NS", "weight": 5.8, "name": "TVS Motor"},
        {"ticker": "ASHOKLEY.NS", "weight": 4.5, "name": "Ashok Leyland"},
    ],
    "^CNXFMCG": [
        {"ticker": "ITC.NS", "weight": 24.5, "name": "ITC"},
        {"ticker": "HINDUNILVR.NS", "weight": 22.8, "name": "Hindustan Unilever"},
        {"ticker": "NESTLEIND.NS", "weight": 12.5, "name": "Nestle India"},
        {"ticker": "BRITANNIA.NS", "weight": 8.2, "name": "Britannia Industries"},
        {"ticker": "TATACONSUM.NS", "weight": 7.5, "name": "Tata Consumer Products"},
        {"ticker": "DABUR.NS", "weight": 6.8, "name": "Dabur India"},
        {"ticker": "GODREJCP.NS", "weight": 5.2, "name": "Godrej Consumer"},
        {"ticker": "COLPAL.NS", "weight": 4.5, "name": "Colgate Palmolive"},
    ],
    "^CNXPHARMA": [
        {"ticker": "SUNPHARMA.NS", "weight": 22.5, "name": "Sun Pharmaceutical"},
        {"ticker": "CIPLA.NS", "weight": 16.8, "name": "Cipla"},
        {"ticker": "DRREDDY.NS", "weight": 14.2, "name": "Dr. Reddy's"},
        {"ticker": "APOLLOHOSP.NS", "weight": 12.5, "name": "Apollo Hospitals"},
        {"ticker": "BIOCON.NS", "weight": 8.5, "name": "Biocon"},
        {"ticker": "TORNTPHARM.NS", "weight": 7.2, "name": "Torrent Pharma"},
        {"ticker": "LUPIN.NS", "weight": 6.8, "name": "Lupin"},
        {"ticker": "ZYDUSLIFE.NS", "weight": 5.5, "name": "Zydus Lifesciences"},
    ],
    "^CNXMETAL": [
        {"ticker": "TATASTEEL.NS", "weight": 25.5, "name": "Tata Steel"},
        {"ticker": "HINDALCO.NS", "weight": 18.8, "name": "Hindalco Industries"},
        {"ticker": "JSWSTEEL.NS", "weight": 16.2, "name": "JSW Steel"},
        {"ticker": "ADANIENT.NS", "weight": 12.5, "name": "Adani Enterprises"},
        {"ticker": "VEDL.NS", "weight": 8.5, "name": "Vedanta"},
        {"ticker": "NMDC.NS", "weight": 6.8, "name": "NMDC"},
        {"ticker": "COALINDIA.NS", "weight": 6.2, "name": "Coal India"},
        {"ticker": "SAIL.NS", "weight": 5.5, "name": "SAIL"},
    ],
    "^CNXREALTY": [
        {"ticker": "DLF.NS", "weight": 28.5, "name": "DLF"},
        {"ticker": "GODREJPROP.NS", "weight": 18.2, "name": "Godrej Properties"},
        {"ticker": "MACOTECH.NS", "weight": 14.5, "name": "Macrotech Developers"},
        {"ticker": "PRESTIGE.NS", "weight": 12.8, "name": "Prestige Estates"},
        {"ticker": "BRIGADE.NS", "weight": 9.5, "name": "Brigade Enterprises"},
        {"ticker": "OBEROIRLTY.NS", "weight": 8.2, "name": "Oberoi Realty"},
        {"ticker": "SOBHA.NS", "weight": 6.5, "name": "Sobha"},
        {"ticker": "PHOENIXLTD.NS", "weight": 5.8, "name": "The Phoenix Mills"},
    ],
    "^CNXENERGY": [
        {"ticker": "RELIANCE.NS", "weight": 38.5, "name": "Reliance Industries"},
        {"ticker": "ONGC.NS", "weight": 18.2, "name": "Oil & Natural Gas"},
        {"ticker": "BPCL.NS", "weight": 12.5, "name": "BPCL"},
        {"ticker": "IOC.NS", "weight": 10.8, "name": "Indian Oil"},
        {"ticker": "HINDPETRO.NS", "weight": 8.5, "name": "Hindustan Petroleum"},
        {"ticker": "GAIL.NS", "weight": 6.8, "name": "GAIL India"},
        {"ticker": "MGL.NS", "weight": 3.2, "name": "Mahanagar Gas"},
        {"ticker": "IGL.NS", "weight": 2.5, "name": "Indraprastha Gas"},
    ],
    "^CNXFIN SERVICE": [
        {"ticker": "HDFCBANK.NS", "weight": 22.5, "name": "HDFC Bank"},
        {"ticker": "ICICIBANK.NS", "weight": 18.8, "name": "ICICI Bank"},
        {"ticker": "SBIN.NS", "weight": 14.2, "name": "SBI"},
        {"ticker": "BAJFINANCE.NS", "weight": 12.5, "name": "Bajaj Finance"},
        {"ticker": "KOTAKBANK.NS", "weight": 10.8, "name": "Kotak Bank"},
        {"ticker": "AXISBANK.NS", "weight": 8.5, "name": "Axis Bank"},
        {"ticker": "BAJAJFINSV.NS", "weight": 6.2, "name": "Bajaj Finserv"},
        {"ticker": "MUTHOOTFIN.NS", "weight": 3.5, "name": "Muthoot Finance"},
    ],
    "^CNXCONSUM": [
        {"ticker": "TATAMOTORS.NS", "weight": 18.5, "name": "Tata Motors"},
        {"ticker": "MARUTI.NS", "weight": 16.2, "name": "Maruti Suzuki"},
        {"ticker": "EICHERMOT.NS", "weight": 12.8, "name": "Eicher Motors"},
        {"ticker": "M&M.NS", "weight": 12.5, "name": "M&M"},
        {"ticker": "TATACONSUM.NS", "weight": 10.8, "name": "Tata Consumer"},
        {"ticker": "BATAINDIA.NS", "weight": 8.5, "name": "Bata India"},
        {"ticker": "VBL.NS", "weight": 7.2, "name": "Varun Beverages"},
        {"ticker": "ADANIPOWER.NS", "weight": 6.5, "name": "Adani Power"},
    ],
    "^CNXMEDIA": [
        {"ticker": "RELIANCE.NS", "weight": 25.5, "name": "Reliance Industries"},
        {"ticker": "ZEEL.NS", "weight": 18.8, "name": "Zee Entertainment"},
        {"ticker": "SUNTV.NS", "weight": 15.2, "name": "Sun TV Network"},
        {"ticker": "NETWORK18.NS", "weight": 12.5, "name": "Network18 Media"},
        {"ticker": "PRAJIND.NS", "weight": 10.8, "name": "Praj Industries"},
        {"ticker": "DISHTV.NS", "weight": 8.5, "name": "Dish TV"},
        {"ticker": "HATHWAY.NS", "weight": 5.2, "name": "Hathway"},
        {"ticker": "DEN.NS", "weight": 4.5, "name": "DEN Networks"},
    ],
    "^CNXPSUBANK": [
        {"ticker": "SBIN.NS", "weight": 32.5, "name": "State Bank of India"},
        {"ticker": "BANKBARODA.NS", "weight": 18.2, "name": "Bank of Baroda"},
        {"ticker": "CANBK.NS", "weight": 14.5, "name": "Canara Bank"},
        {"ticker": "PNB.NS", "weight": 12.8, "name": "Punjab National Bank"},
        {"ticker": "UNIONBANK.NS", "weight": 9.5, "name": "Union Bank"},
        {"ticker": "IOB.NS", "weight": 7.2, "name": "Indian Overseas Bank"},
        {"ticker": "CENTRALBK.NS", "weight": 3.5, "name": "Central Bank"},
        {"ticker": "UCOBANK.NS", "weight": 2.8, "name": "UCO Bank"},
    ],
    "^CNXINFRA": [
        {"ticker": "ADANIPORTS.NS", "weight": 18.5, "name": "Adani Ports"},
        {"ticker": "LT.NS", "weight": 16.2, "name": "Larsen & Toubro"},
        {"ticker": "TATASTEEL.NS", "weight": 14.8, "name": "Tata Steel"},
        {"ticker": "JSWSTEEL.NS", "weight": 12.5, "name": "JSW Steel"},
        {"ticker": "ADANIENT.NS", "weight": 10.8, "name": "Adani Enterprises"},
        {"ticker": "GRINFRA.NS", "weight": 8.5, "name": "G R Infraprojects"},
        {"ticker": "IRB.NS", "weight": 6.8, "name": "IRB Infrastructure"},
        {"ticker": "KALPATPOW.NS", "weight": 5.2, "name": "Kalpataru Power"},
    ],
    "^CNXMID50": [
        {"ticker": "CROMPTON.NS", "weight": 5.2, "name": "Crompton Greaves"},
        {"ticker": "METROBRAND.NS", "weight": 4.8, "name": "Metro Brands"},
        {"ticker": "KALPATCOMPO.NS", "weight": 4.5, "name": "Kalpataru Components"},
        {"ticker": "RATNAMANI.NS", "weight": 4.2, "name": "Ratnamani Metals"},
        {"ticker": "KIRLOSKAR.NS", "weight": 3.8, "name": "Kirloskar Oil"},
        {"ticker": "FINOLEXIND.NS", "weight": 3.5, "name": "Finolex Industries"},
        {"ticker": "GMMPFAUDLR.NS", "weight": 3.2, "name": "GMM Pfaudler"},
        {"ticker": "NITCO.NS", "weight": 3.0, "name": "Nitco"},
    ],
}

BENCHMARK = "^NSEI"

TICKERS = {
    "India_Equity": ["RELIANCE.NS", "HDFCBANK.NS", "TCS.NS", "INFY.NS", "BHARTIARTL.NS", "ITC.NS"],
    "India_ETF":    ["NIFTYBEES.NS", "GOLDBEES.NS", "LIQUIDBEES.NS"],
    "India_Sectors": list(NIFTY_SECTORALS.keys()) + [BENCHMARK],
    "US_Equity":    ["AAPL", "MSFT", "TSLA", "GOOGL", "AMZN"],
    "US_ETF":       ["SPY", "QQQ", "GLD", "TLT", "VNQ"],
}
ALL_TICKERS = [t for grp in TICKERS.values() for t in grp]

RSS_FEEDS = {
    "Moneycontrol Markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Livemint Markets": "https://www.livemint.com/rss/markets",
    "Yahoo Finance India": "https://in.finance.yahoo.com/rss/topstories",
}

SECTOR_MAP = {
    "Technology"  : ["tech", "software", "ai", "cloud", "semiconductor", "aapl", "msft", "googl", "tcs", "infosys", "infy", "tsla", "azure", "iphone"],
    "Finance"     : ["bank", "interest rate", "rbi", "fed", "repo", "credit", "nbfc", "hdfc", "nse", "bse", "rate cut", "rate hike", "monetary"],
    "Energy"      : ["oil", "crude", "opec", "gas", "energy", "reliance", "ongc", "petroleum", "renewable", "solar", "green energy", "capex"],
    "Gold/Metals" : ["gold", "precious metals", "goldbees", "gld", "safe haven", "₹85,000"],
    "Macro"       : ["inflation", "gdp", "recession", "cpi", "ppi", "fiscal", "federal reserve", "rbi", "monetary policy", "growth rate", "economic"],
    "Real Estate" : ["reit", "property", "housing", "realty", "vnq", "real estate"],
    "Consumer"    : ["retail", "fmcg", "consumer", "sales", "revenue", "earnings", "iphone"],
}

CLIENT_PROFILES = [
    {
        "client_id": "HSBC-WM-0001", "name": "Rajesh Iyer", "age": 58, "occupation": "Retired IAS Officer",
        "geo": "India (Chennai)", "risk_tolerance": "Conservative", "investment_horizon": 5, "liquidity_need": "High",
        "total_aum": 8500000, "annual_income": 1800000, "tax_bracket": "30%", "kyc_status": "Verified",
        "financial_goal": "Capital preservation & regular income",
        "portfolio": {"HDFCBANK.NS": 0.12, "NIFTYBEES.NS": 0.15, "GOLDBEES.NS": 0.20, "LIQUIDBEES.NS": 0.20, "TLT": 0.10, "Cash": 0.23}
    },
    {
        "client_id": "HSBC-WM-0002", "name": "Priya Sharma", "age": 32, "occupation": "Principal Data Scientist, Bengaluru",
        "geo": "India (Bengaluru)", "risk_tolerance": "Aggressive", "investment_horizon": 20, "liquidity_need": "Low",
        "total_aum": 4200000, "annual_income": 4500000, "tax_bracket": "30%", "kyc_status": "Verified",
        "financial_goal": "Wealth creation & early retirement corpus",
        "portfolio": {"INFY.NS": 0.15, "TCS.NS": 0.12, "RELIANCE.NS": 0.10, "AAPL": 0.15, "MSFT": 0.13, "TSLA": 0.10, "QQQ": 0.15, "Cash": 0.10}
    },
    {
        "client_id": "HSBC-WM-0003", "name": "Michael Chen", "age": 47, "occupation": "Managing Director, Private Equity",
        "geo": "Singapore", "risk_tolerance": "Moderate", "investment_horizon": 12, "liquidity_need": "Medium",
        "total_aum": 6200000, "annual_income": 1800000, "tax_bracket": "22%", "kyc_status": "Verified",
        "financial_goal": "Balanced growth & international diversification",
        "portfolio": {"AAPL": 0.12, "MSFT": 0.10, "GOOGL": 0.08, "SPY": 0.20, "GLD": 0.10, "VNQ": 0.10, "RELIANCE.NS": 0.08, "HDFCBANK.NS": 0.07, "TLT": 0.10, "Cash": 0.05}
    }
]

def fetch_market_data():
    print("📡 Fetching 90-day price data...")
    end_date = datetime.today()
    start_date = end_date - timedelta(days=90)
    
    price_data = {}
    for ticker in ALL_TICKERS:
        try:
            hist = yf.Ticker(ticker).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            if not hist.empty:
                price_data[ticker] = hist["Close"]
        except Exception:
            pass
    
    closing_prices = pd.DataFrame(price_data)
    if not closing_prices.empty:
        closing_prices.index = pd.to_datetime(closing_prices.index).tz_localize(None)
    closing_prices.to_csv("data/raw/prices.csv")
    print(f"📊 Market Data saved: {len(closing_prices)} rows.")

def fetch_financial_news():
    print("📰 Fetching news from RSS feeds...")
    news_items = []
    
    for source, url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
                # Attempt to parse date
                published_dt = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_dt = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, 'published'):
                    try:
                        published_dt = date_parser.parse(entry.published)
                        if published_dt.tzinfo:
                            published_dt = published_dt.replace(tzinfo=None)
                    except:
                        pass

                news_items.append({
                    "source": source,
                    "title": entry.get("title", ""),
                    "summary": entry.get("summary", ""),
                    "published": published_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "published_dt": published_dt,
                    "full_text": f"{entry.get('title', '')}. {entry.get('summary', '')}"
                })
        except Exception:
            pass
        
    news_df = pd.DataFrame(news_items)
    if not news_df.empty:
        # Sort by date descending
        news_df = news_df.sort_values(by="published_dt", ascending=False)
        # Keep top 40 unique titles
        news_df = news_df.drop_duplicates(subset=["title"]).head(40)
        # Drop the helper column
        news_df = news_df.drop(columns=["published_dt"])
        
    news_df.to_csv("data/raw/news.csv", index=False)
    print(f"📰 News Data saved: {len(news_df)} articles.")
    return news_df

def generate_clients():
    flat = []
    for c in CLIENT_PROFILES:
        flat.append({
            "client_id": c["client_id"], "name": c["name"], "age": c["age"],
            "geo": c["geo"], "risk_tolerance": c["risk_tolerance"],
            "investment_horizon": c["investment_horizon"], "liquidity_need": c["liquidity_need"],
            "total_aum": c["total_aum"], "financial_goal": c["financial_goal"],
            "portfolio_json": json.dumps(c["portfolio"]),
        })
    pd.DataFrame(flat).to_csv("data/clients/client_profiles.csv", index=False)
    with open("data/clients/client_profiles.json", "w") as f:
        json.dump(CLIENT_PROFILES, f, indent=2)
    print("👤 Client Profiles generated.")

def clean_text(text: str) -> str:
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'http\S+|www\S+', '', text)
    return re.sub(r'\s+', ' ', text).strip()

def detect_sector(text: str) -> str:
    tl = text.lower()
    for sector, kws in SECTOR_MAP.items():
        if any(k in tl for k in kws):
            return sector
    return "General"

def preprocess_news(news_df):
    processed = []
    chunk_id = 0
    for _, row in news_df.iterrows():
        clean = clean_text(str(row.get("full_text", "")))
        words = clean.split()
        
        # Simple windowing
        for i in range(0, len(words), 360):
            chunk = " ".join(words[i:i+400])
            if len(chunk.split()) < 8: continue
            
            processed.append({
                "chunk_id": f"chunk_{chunk_id:04d}",
                "source": row.get("source", "Unknown"),
                "text": chunk,
                "sector": detect_sector(chunk),
                "published": row.get("published", "")
            })
            chunk_id += 1
            
    df = pd.DataFrame(processed)
    df.to_csv("data/processed/chunks.csv", index=False)
    print(f"✅ NLP Preprocessing complete. Generated {len(processed)} chunks.")

def run_pipeline():
    fetch_market_data()
    news_df = fetch_financial_news()
    preprocess_news(news_df)
    generate_clients()

def fetch_sector_data(days=90):
    print("📡 Fetching sector index data for RRG analysis...")
    end_date = datetime.today()
    start_date = end_date - timedelta(days=days)
    
    all_tickers = list(NIFTY_SECTORALS.keys()) + [BENCHMARK]
    price_data = {}
    
    for ticker in all_tickers:
        try:
            hist = yf.Ticker(ticker).history(start=start_date.strftime("%Y-%m-%d"), end=end_date.strftime("%Y-%m-%d"))
            if not hist.empty:
                price_data[ticker] = hist["Close"]
        except Exception:
            pass
    
    df = pd.DataFrame(price_data)
    if not df.empty:
        df.index = pd.to_datetime(df.index).tz_localize(None)
    return df

def calculate_rsmratio(series, benchmark, period=20):
    rs = series / benchmark
    rsm_ratio = rs.rolling(period).mean()
    return rsm_ratio

def calculate_momentum(series, period=20):
    roc = (series - series.shift(period)) / series.shift(period) * 100
    roc_smooth = roc.rolling(4).mean()
    return roc_smooth

def calculate_rrg_coordinates(sector_prices, benchmark_prices, period=20):
    rrg_data = []
    
    for ticker in sector_prices.columns:
        if ticker == BENCHMARK:
            continue
        
        sector = sector_prices[ticker].dropna()
        bench = benchmark_prices.dropna()
        
        common_idx = sector.index.intersection(bench.index)
        if len(common_idx) < period + 5:
            continue
        
        sector_aligned = sector.loc[common_idx]
        bench_aligned = bench.loc[common_idx]
        
        rs_ratio = calculate_rsmratio(sector_aligned, bench_aligned, period)
        momentum = calculate_momentum(rs_ratio, period)
        
        latest_rs = rs_ratio.dropna().iloc[-1] if not rs_ratio.dropna().empty else 0
        latest_mom = momentum.dropna().iloc[-1] if not momentum.dropna().empty else 0
        
        prev_rs = rs_ratio.dropna().iloc[-5] if len(rs_ratio.dropna()) >= 5 else latest_rs
        prev_mom = momentum.dropna().iloc[-5] if len(momentum.dropna()) >= 5 else latest_mom
        
        rs_change = latest_rs - prev_rs
        mom_change = latest_mom - prev_mom
        
        if rs_change > 0 and mom_change > 0:
            quadrant = "Leading"
        elif rs_change > 0 and mom_change <= 0:
            quadrant = "Weakening"
        elif rs_change <= 0 and mom_change > 0:
            quadrant = "Improving"
        else:
            quadrant = "Lagging"
        
        sector_return = ((sector_aligned.iloc[-1] / sector_aligned.iloc[-period]) - 1) * 100 if len(sector_aligned) >= period else 0
        bench_return = ((bench_aligned.iloc[-1] / bench_aligned.iloc[-period]) - 1) * 100 if len(bench_aligned) >= period else 0
        
        rrg_data.append({
            "ticker": ticker,
            "name": NIFTY_SECTORALS.get(ticker, ticker),
            "rs_ratio": round(latest_rs, 4),
            "momentum": round(latest_mom, 2),
            "quadrant": quadrant,
            "sector_return": round(sector_return, 2),
            "bench_return": round(bench_return, 2),
            "relative_return": round(sector_return - bench_return, 2),
            "rs_change": round(rs_change, 4),
            "mom_change": round(mom_change, 2),
        })
    
    return pd.DataFrame(rrg_data)

def calculate_market_breadth(sector_prices, days=5):
    breadth_data = {}
    
    returns = sector_prices.pct_change()
    
    advancing = (returns > 0).sum(axis=1)
    declining = (returns < 0).sum(axis=1)
    
    for i, (date, row) in enumerate(returns.iterrows()):
        if i < days:
            continue
        
        window = returns.iloc[max(0, i-days):i+1]
        adv = (window > 0).sum().sum()
        dec = (window < 0).sum().sum()
        total = adv + dec
        breadth_pct = (adv / total * 100) if total > 0 else 50
        
        breadth_data[date] = {
            "advancing": adv,
            "declining": dec,
            "breadth_pct": round(breadth_pct, 1),
            "date": date.strftime("%Y-%m-%d")
        }
    
    breadth_df = pd.DataFrame.from_dict(breadth_data, orient="index")
    return breadth_df.tail(20).to_dict(orient="records")

def generate_sector_rotation_report(days=90):
    print("📊 Generating Institutional Sector Rotation Report...")
    
    sector_prices = fetch_sector_data(days)
    
    if sector_prices.empty:
        print("⚠️ No sector data available")
        return {"error": "No sector data available"}
    
    benchmark_prices = sector_prices[BENCHMARK] if BENCHMARK in sector_prices.columns else sector_prices.iloc[:, 0]
    sector_only = sector_prices.drop(columns=[BENCHMARK], errors='ignore')
    
    rrg_df = calculate_rrg_coordinates(sector_only, benchmark_prices, period=20)
    
    breadth = calculate_market_breadth(sector_prices, days=5)
    
    quadrant_summary = {
        "Leading": rrg_df[rrg_df["quadrant"] == "Leading"].to_dict("records"),
        "Weakening": rrg_df[rrg_df["quadrant"] == "Weakening"].to_dict("records"),
        "Improving": rrg_df[rrg_df["quadrant"] == "Improving"].to_dict("records"),
        "Lagging": rrg_df[rrg_df["quadrant"] == "Lagging"].to_dict("records"),
    }
    
    latest_breadth = breadth[-1] if breadth else {"advancing": 0, "declining": 0, "breadth_pct": 50}
    
    # NEW: Identify the actual Advancers and Decliners for the "Market Pulse"
    last_returns = sector_prices.pct_change().iloc[-1]
    advancers_list = last_returns[last_returns > 0].sort_values(ascending=False)
    decliners_list = last_returns[last_returns < 0].sort_values(ascending=True)

    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "market_breadth": {
            "current": latest_breadth,
            "history": breadth[-10:] if len(breadth) > 10 else breadth,
            "signal": "Bullish" if latest_breadth["breadth_pct"] > 60 else "Bearish" if latest_breadth["breadth_pct"] < 40 else "Neutral",
            "breadth_details": {
                "top_advancers": [{"name": NIFTY_SECTORALS.get(k, k).replace("^", ""), "change": round(v*100, 2)} for k, v in advancers_list.head(10).items()],
                "top_decliners": [{"name": NIFTY_SECTORALS.get(k, k).replace("^", ""), "change": round(v*100, 2)} for k, v in decliners_list.head(10).items()]
            }
        },
        "rrg_coordinates": rrg_df.to_dict("records"),
        "quadrants": quadrant_summary,
        "summary": {
            "total_sectors": len(rrg_df),
            "leading_count": len(rrg_df[rrg_df["quadrant"] == "Leading"]),
            "weakening_count": len(rrg_df[rrg_df["quadrant"] == "Weakening"]),
            "improving_count": len(rrg_df[rrg_df["quadrant"] == "Improving"]),
            "lagging_count": len(rrg_df[rrg_df["quadrant"] == "Lagging"]),
        },
        "top_performers": rrg_df.nlargest(3, "relative_return")[["name", "relative_return", "quadrant"]].to_dict("records"),
        "bottom_performers": rrg_df.nsmallest(3, "relative_return")[["name", "relative_return", "quadrant"]].to_dict("records"),
    }
    
    with open("data/processed/sector_rotation_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"✅ Sector Rotation Report generated: {len(rrg_df)} sectors analyzed")
    return report

if __name__ == "__main__":
    run_pipeline()
    generate_sector_rotation_report()
