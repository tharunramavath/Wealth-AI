import re
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from functools import lru_cache

RSS_FEEDS = {
    "Moneycontrol Markets": "https://www.moneycontrol.com/rss/marketreports.xml",
    "Economic Times Markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
    "Livemint Markets": "https://www.livemint.com/rss/markets",
    "Yahoo Finance India": "https://in.finance.yahoo.com/rss/topstories",
}

SECTOR_MAP = {
    "Technology": ["tcs", "infosys", "infy", "wipro", "hcltech", "tech mahindra", "digital india", "it services", "saas"],
    "Finance": ["bank", "interest rate", "rbi", "sebi", "repo", "credit", "nbfc", "hdfc", "icici", "sbi", "kotak", "axis bank", "nse", "bse", "monetary policy", "inflation"],
    "Energy": ["reliance", "ril", "ongc", "ntpc", "adani green", "tata power", "oil", "gas", "petroleum", "renewable", "solar", "green hydrogen"],
    "Automobile": ["tata motors", "maruti", "mahindra", "m&m", "bajaj auto", "eicher", "ev", "fame ii", "auto sales"],
    "Consumer/FMCG": ["itc", "hindustan unilever", "hul", "nestle", "britannia", "fmcg", "retail", "rural demand"],
    "Gold/Metals": ["gold", "silver", "goldbees", "titan", "muthoot", "manappuram", "precious metals"],
    "Macro": ["budget", "gst", "gdp", "fiscal deficit", "rbi policy", "monetary policy", "growth rate", "economic survey", "nifty", "sensex"],
    "Real Estate": ["realty", "dlf", "godrej properties", "oberoi", "rera", "housing demand", "property rates"],
}

POSITIVE_KEYWORDS = ["growth", "profit", "surge", "rally", "gain", "rise", "bullish", "upgrade", "high", "record", "best", "beat", "jump"]
NEGATIVE_KEYWORDS = ["loss", "decline", "fall", "plunge", "bearish", "downgrade", "risk", "concern", "low", "worst", "miss", "drop", "cut"]

LIVE_NEWS_CACHE_TTL_MINUTES = 15


@lru_cache(maxsize=1)
def _get_cached_news(max_articles: int = 30) -> tuple:
    cache_time = datetime.now()
    news_items = _fetch_all_feeds(max_articles)
    return (news_items, cache_time.isoformat())


def _fetch_all_feeds(max_articles: int) -> List[Dict]:
    import urllib.request
    news_items = []
    
    for source, url in RSS_FEEDS.items():
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                feed = feedparser.parse(response)
            for entry in feed.entries[:15]:
                published_dt = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published_dt = datetime(*entry.published_parsed[:6])
                    except:
                        pass
                
                title = entry.get('title', '')
                summary = _strip_html(entry.get('summary', ''))
                text = f"{title}. {summary}"
                
                sector = _detect_sector(text)
                sentiment = _detect_sentiment(text)
                
                news_items.append({
                    "chunk_id": f"live_{len(news_items)}",
                    "source": source,
                    "text": f"{title} - {summary}"[:500],
                    "sector": sector,
                    "event_type": "Market Update",
                    "dominant_sentiment": sentiment,
                    "published": published_dt.strftime("%Y-%m-%d %H:%M:%S"),
                })
        except Exception as e:
            print(f"Failed to fetch from {source}: {e}")
            continue
    
    news_items.sort(key=lambda x: x["published"], reverse=True)
    return news_items[:max_articles]


def _detect_sector(text: str) -> str:
    tl = text.lower()
    for sector, keywords in SECTOR_MAP.items():
        if any(k in tl for k in keywords):
            return sector
    return "General"


def _detect_sentiment(text: str) -> str:
    tl = text.lower()
    positive_count = sum(1 for k in POSITIVE_KEYWORDS if k in tl)
    negative_count = sum(1 for k in NEGATIVE_KEYWORDS if k in tl)
    
    if positive_count > negative_count:
        return "Positive"
    elif negative_count > positive_count:
        return "Negative"
    return "Neutral"


def _strip_html(text: str) -> str:
    clean = re.sub(r'<[^>]+>', '', text)
    clean = re.sub(r'http\S+', '', clean)
    return ' '.join(clean.split())


def fetch_live_news(max_articles: int = 30) -> List[Dict]:
    now = datetime.now()
    try:
        cached_news, cache_time_str = _get_cached_news(max_articles)
        cache_time = datetime.fromisoformat(cache_time_str)
        
        if (now - cache_time).total_seconds() < (LIVE_NEWS_CACHE_TTL_MINUTES * 60):
            return cached_news[:max_articles]
    except Exception:
        pass
    
    _get_cached_news.cache_clear()
    cached_news, _ = _get_cached_news(max_articles)
    return cached_news[:max_articles]


def get_news_source_info() -> Dict:
    return {
        "feeds": list(RSS_FEEDS.keys()),
        "cache_ttl_minutes": LIVE_NEWS_CACHE_TTL_MINUTES,
        "last_updated": datetime.now().isoformat()
    }
