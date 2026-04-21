import os
import json
import time
import threading
from src.nba_engine import generate_nba
from src.compliance import load_client_profile
from src.event_fetcher import fetch_market_news, get_events_for_portfolio

POLLING_INTERVAL_MINUTES = 15
_event_polling_thread = None
_last_events = []

def get_recent_events():
    """Return cached recent events."""
    global _last_events
    return _last_events

def fetch_live_events(max_articles=20):
    """Fetch real market events from Alpha Vantage."""
    global _last_events
    _last_events = fetch_market_news(max_articles=max_articles)
    return _last_events

def find_vulnerable_clients(sector: str):
    """Queries the client database to find who has exposure to the affected sector."""
    try:
        with open("data/clients/client_profiles.json", "r") as f:
            profiles = json.load(f)
    except FileNotFoundError:
        print("Run data pipeline first.")
        return []

    # Simple heuristic: If a client has > 5% in tech stocks, trigger them if Tech event.
    # We will use the SECTOR_MAP from structured_db.
    from src.structured_db import SECTOR_MAP
    sector_tickers = SECTOR_MAP.get(sector, [])

    vulnerable = []
    for p in profiles:
        portfolio = p.get("portfolio", {})
        exposure = 0.0
        for ticker, weight in portfolio.items():
            if ticker in sector_tickers:
                exposure += weight
        
        if exposure > 0.05:
            vulnerable.append({"client_id": p["client_id"], "name": p["name"], "exposure": exposure})
            
    return vulnerable

def run_event_driven_architecture():
    print("🚀 [Trigger Engine] Fetching real-time market events from Alpha Vantage...\n")
    events = fetch_market_news(max_articles=20)
    
    for event in events:
        print(f"🔔 [NEW EVENT]: {event.get('headline', 'N/A')[:60]}... (Sector: {event.get('sector', 'Unknown')} | Severity: {event.get('severity', 'Low')})")
        
        if event.get("severity") not in ["Critical", "High"]:
            print(f"  -> Low severity event, skipping client triggers.\n")
            continue
        
        # 1. Identify blast radius
        affected_clients = find_vulnerable_clients(event["sector"])
        
        if not affected_clients:
            print(f"  -> No clients significantly exposed to {event['sector']}.\n")
            continue
            
        print(f"  -> [Blast Radius] Found {len(affected_clients)} vulnerable clients. Triggering auto-NBAs...")
        
        # 2. Trigger NBA Generation
        for client in affected_clients:
            print(f"     ⚙️ Processing {client['client_id']} ({client['name']}) - Exposure: {client['exposure']:.1%}")
            if "NVIDIA_API_KEY" in os.environ or "GEMINI_API_KEY" in os.environ:
                start_time = time.time()
                result = generate_nba(client["client_id"], triggering_event=event)
                latency = time.time() - start_time
                
                if "error" in result:
                    print(f"        ❌ Failed: {result['error']}")
                else:
                    action = result.get("next_best_action", "Hold")
                    if isinstance(action, dict):
                        action = action.get("action", "Hold")
                    flags = result.get("flags", [])
                    status = "✅ APPROVED" if not flags else f"🛑 BLOCKED ({len(flags)} violations)"
                    print(f"        -> Action: {str(action)[:80]} | {status} | Latency: {latency:.2f}s")
            else:
                print("        -> Skipped: API key missing.")
        print("-" * 60)

def _polling_loop():
    """Background polling loop - runs every 15 minutes."""
    global _event_polling_thread
    print(f"⏰ Event polling started - checking every {POLLING_INTERVAL_MINUTES} minutes")
    
    while _event_polling_thread is not None and _event_polling_thread.is_alive():
        try:
            print("\n" + "="*60)
            print(f"🕐 [{time.strftime('%Y-%m-%d %H:%M:%S')}] Running scheduled event scan...")
            run_event_driven_architecture()
            print("="*60)
        except Exception as e:
            print(f"❌ Polling error: {e}")
        
        time.sleep(POLLING_INTERVAL_MINUTES * 60)

def start_event_polling():
    """Start background polling thread."""
    global _event_polling_thread
    if _event_polling_thread is not None and _event_polling_thread.is_alive():
        print("⚠️ Polling already running")
        return False
    
    _event_polling_thread = threading.Thread(target=_polling_loop, daemon=True)
    _event_polling_thread.start()
    print(f"✅ Event polling started in background (every {POLLING_INTERVAL_MINUTES} min)")
    return True

def stop_event_polling():
    """Stop background polling thread."""
    global _event_polling_thread
    if _event_polling_thread is None:
        print("⚠️ No polling thread running")
        return False
    
    _event_polling_thread = None
    print("✅ Event polling stopped")
    return True

def trigger_manual_scan():
    """Manually trigger an event scan immediately."""
    print("\n🚀 [MANUAL TRIGGER] Starting event scan...")
    run_event_driven_architecture()
    return get_recent_events()

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    run_event_driven_architecture()
