import os
import requests
from dotenv import load_dotenv

load_dotenv()

POS_WORDS = ["surge", "gain", "rise", "beat", "record", "rally", "bullish", "growth", "strong", "upgrade"]
NEG_WORDS = ["decline", "fell", "drop", "loss", "miss", "fall", "bearish", "risk", "concern", "downgrade", "weaker"]

EVENT_MAP = {
    "rate_change": ["rate cut", "rate hike", "repo rate", "fed funds", "basis points", "bps", "rbi", "federal reserve", "monetary policy", "interest rate"],
    "earnings": ["quarterly earnings", "eps", "revenue", "profit", "beats", "misses", "q1", "q2", "q3", "q4", "guidance", "annual results"],
    "geopolitics": ["war", "sanctions", "geopolitical", "conflict", "opec", "trade war", "export ban", "import restrictions", "escalation"],
    "inflation": ["inflation", "cpi", "ppi", "consumer price", "wholesale price", "cost of living", "price rise", "deflation"],
    "sector_shock": ["sector decline", "disruption", "layoffs", "supply chain", "shortage", "regulation", "visa", "policy changes"],
    "macro": ["gdp", "recession", "slowdown", "growth rate", "economic outlook", "fiscal deficit", "current account", "capex"]
}

finbert = None
USE_FINBERT = False

try:
    from transformers import pipeline
    finbert = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True, max_length=512, device=-1)
    USE_FINBERT = True
    print("[OK] FinBERT loaded successfully")
except Exception as e:
    print(f"[WARN] FinBERT unavailable ({e}). Fallback to rule-based sentiment.")

def get_sentiment(text: str) -> dict:
    if USE_FINBERT and finbert:
        result = finbert(text[:900])[0]
        sentiment_dict = {}
        for r in result:
            label = str(r.get("label", "neutral")).lower()
            score = float(r.get("score", 0))
            sentiment_dict[label] = round(score, 4)
        return sentiment_dict
    
    tl = text.lower()
    p = sum(1 for w in POS_WORDS if w in tl)
    n = sum(1 for w in NEG_WORDS if w in tl)
    total = p + n + 1
    return {"positive": round(p/total, 3), "negative": round(n/total, 3), "neutral": round(1-(p+n)/total, 3)}

def classify_event(text: str) -> str:
    tl = text.lower()
    for event, kws in EVENT_MAP.items():
        if any(k in tl for k in kws):
            return event
    return "general_news"

ALPHA_VANTAGE_API_KEY = os.environ.get("Alpha_vantage_Api", "")

SECTOR_KEYWORDS = {
    "Technology": ["tech", "software", "ai", "chip", "semiconductor", "apple", "microsoft", "google", "amazon", "tesla", "nvidia", "tcs", "infosys"],
    "Financials": ["bank", "finance", "interest rate", "fed", "rate hike", "hdfc", "banking", "credit", "loan"],
    "Energy": ["oil", "gas", "energy", "opec", "crude", "petroleum", "reliance", "renewable"],
    "Commodity/Gold": ["gold", "silver", "commodity", "precious metal", "gld"],
    "Consumer": ["consumer", "retail", "itc", "fmcg", "food", "beverage"],
    "Telecom": ["telecom", "airtel", "jio", "wireless", "5g"],
    "Real Estate": ["real estate", "property", "housing", "reit"],
    "Broad Market": ["market", "index", "spy", "nifty", "sensex", "sp500", "rally", "correction"]
}

def fetch_market_news(max_articles=20):
    """Fetch real market news from Alpha Vantage News Sentiment API."""
    if not ALPHA_VANTAGE_API_KEY:
        print("[WARN] Alpha_vantage_Api not configured in .env")
        return []
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "apikey": ALPHA_VANTAGE_API_KEY,
            "limit": max_articles,
            "sort": "LATEST"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "feed" not in data:
            print(f"[WARN] Alpha Vantage error: {data.get('Note', 'Unknown error')}")
            return []
        
        events = []
        for article in data.get("feed", [])[:max_articles]:
            if not article:
                continue
            
            title = str(article.get("title") or "")
            summary = str(article.get("summary") or "")[:200]
            text = f"{title} {summary}"
            
            sentiment = get_sentiment(text)
            event_type = classify_event(text)
            sector = _identify_sector(text)
            severity = _calculate_severity(sentiment, event_type)
            
            banner = article.get("banner_image")
            banner_str = str(banner) if banner else str(len(events))
            events.append({
                "event_id": f"EV-{banner_str[:8]}-{len(events)+1}",
                "headline": title,
                "summary": summary,
                "sector": sector,
                "severity": severity,
                "sentiment": sentiment,
                "event_type": event_type,
                "source": str(article.get("source") or "Unknown"),
                "url": str(article.get("url") or ""),
                "time": str(article.get("time_published") or "")
            })
        
        print(f"[OK] Fetched {len(events)} real market events from Alpha Vantage")
        return events
        
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Network error fetching news: {e}")
        return []
    except Exception as e:
        print(f"[WARN] Error processing news: {e}")
        return []

def fetch_ticker_news(ticker, max_articles=10):
    """Fetch news for a specific ticker."""
    if not ALPHA_VANTAGE_API_KEY:
        return []
    
    try:
        url = "https://www.alphavantage.co/query"
        params = {
            "function": "NEWS_SENTIMENT",
            "tickers": ticker,
            "apikey": ALPHA_VANTAGE_API_KEY,
            "limit": max_articles,
            "sort": "LATEST"
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if "feed" not in data:
            return []
        
        events = []
        for article in data.get("feed", [])[:max_articles]:
            sentiment = get_sentiment(article.get("title", ""))
            events.append({
                "headline": article.get("title", ""),
                "summary": article.get("summary", "")[:200],
                "sentiment": sentiment,
                "source": article.get("source", "Unknown"),
                "time": article.get("time_published", "")
            })
        
        return events
        
    except Exception as e:
        print(f"⚠️ Error fetching ticker news: {e}")
        return []

def _identify_sector(text):
    """Identify which sector an article belongs to based on keywords."""
    text_lower = text.lower()
    
    for sector, keywords in SECTOR_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                return sector
    
    return "Broad Market"

def _calculate_severity(sentiment, event_type):
    """Calculate event severity based on sentiment and event type."""
    negative_score = sentiment.get("negative", 0)
    positive_score = sentiment.get("positive", 0)
    
    extreme_sentiment = max(negative_score, positive_score)
    
    critical_events = ["geopolitics", "rate_change", "sector_shock"]
    high_events = ["earnings", "inflation"]
    
    if event_type in critical_events and extreme_sentiment > 0.4:
        return "Critical"
    elif event_type in high_events and extreme_sentiment > 0.3:
        return "High"
    elif extreme_sentiment > 0.5:
        return "High"
    elif extreme_sentiment > 0.3:
        return "Medium"
    else:
        return "Low"

def get_events_for_portfolio(portfolio_sectors, max_articles=20):
    """Fetch and filter events relevant to portfolio sectors."""
    all_events = fetch_market_news(max_articles)
    
    if not all_events:
        return []
    
    relevant_events = []
    for event in all_events:
        if event["sector"] in portfolio_sectors:
            relevant_events.append(event)
        elif event["severity"] in ["Critical", "High"]:
            relevant_events.append(event)
    
    return relevant_events

if __name__ == "__main__":
    events = fetch_market_news(max_articles=10)
    for e in events:
        print(f"[{e['severity']}] {e['sector']}: {e['headline'][:80]}...")
        print(f"   Sentiment: {e['sentiment']}")
        print()
