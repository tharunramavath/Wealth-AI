import pandas as pd
from transformers import pipeline

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

try:
    finbert = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True, max_length=512, device=-1)
    USE_FINBERT = True
    print("✅ FinBERT loaded successfully")
except Exception as e:
    print(f"⚠️ FinBERT unavailable ({e}). Fallback to rule-based sentiment.")
    USE_FINBERT = False

def get_sentiment(text: str) -> dict:
    if USE_FINBERT:
        result = finbert(text[:900])[0]
        return {r["label"].lower(): round(r["score"], 4) for r in result}
    
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

def detect_events():
    print("🔍 Analysing chunks with FinBERT/rules...")
    chunks_df = pd.read_csv("data/processed/chunks.csv")
    enriched = []
    
    for _, row in chunks_df.iterrows():
        text = str(row["text"])
        sent = get_sentiment(text)
        dominant = max(sent, key=sent.get)
        event = classify_event(text)
        
        enriched.append({
            **row.to_dict(),
            "sentiment_positive": sent.get("positive", 0),
            "sentiment_negative": sent.get("negative", 0),
            "sentiment_neutral": sent.get("neutral", 0),
            "dominant_sentiment": dominant,
            "event_type": event,
        })
        
    enriched_df = pd.DataFrame(enriched)
    enriched_df.to_csv("data/processed/classified_events.csv", index=False)
    print(f"✅ Event Detection complete. Saved {len(enriched_df)} enriched chunks.")

if __name__ == "__main__":
    detect_events()
