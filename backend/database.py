import sqlite3
import hashlib
import os
import json
import uuid
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "platform.db")

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = _conn()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            country TEXT,
            phone TEXT,
            occupation TEXT,
            experience_level TEXT,
            account_type TEXT DEFAULT 'free',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS risk_profiles (
            user_id TEXT PRIMARY KEY,
            risk_tolerance TEXT,
            investment_horizon TEXT,
            goals TEXT,
            liquidity_need TEXT,
            portfolio_size TEXT,
            completed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS portfolios (
            entry_id TEXT PRIMARY KEY,
            user_id TEXT,
            ticker TEXT,
            company_name TEXT,
            quantity REAL,
            avg_price REAL,
            asset_type TEXT,
            sector TEXT,
            industry TEXT,
            exchange TEXT,
            currency TEXT,
            date_bought TEXT,
            added_at TEXT
        );
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id TEXT PRIMARY KEY,
            user_id TEXT,
            message TEXT,
            alert_type TEXT,
            is_read INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS nba_history (
            rec_id TEXT PRIMARY KEY,
            user_id TEXT,
            market_insight TEXT,
            portfolio_impact TEXT,
            next_best_action TEXT,
            confidence_score REAL,
            flags TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS chat_history (
            msg_id TEXT PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            content TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS stock_analysis_cache (
            cache_id TEXT PRIMARY KEY,
            user_id TEXT,
            ticker TEXT,
            ai_analysis TEXT,
            personalized_context TEXT,
            generated_at TEXT,
            UNIQUE(user_id, ticker)
        );
        CREATE TABLE IF NOT EXISTS portfolio_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            created_at TEXT,
            UNIQUE(user_id, ticker, date)
        );
        CREATE INDEX IF NOT EXISTS idx_portfolio_history_user ON portfolio_price_history(user_id);
        CREATE INDEX IF NOT EXISTS idx_portfolio_history_ticker ON portfolio_price_history(ticker);
        CREATE INDEX IF NOT EXISTS idx_portfolio_history_date ON portfolio_price_history(date);
        CREATE TABLE IF NOT EXISTS stock_price_cache (
            cache_id TEXT PRIMARY KEY,
            ticker TEXT NOT NULL,
            date TEXT NOT NULL,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            cached_at TEXT,
            UNIQUE(ticker, date)
        );
        CREATE INDEX IF NOT EXISTS idx_cache_ticker ON stock_price_cache(ticker);
        CREATE INDEX IF NOT EXISTS idx_cache_cached_at ON stock_price_cache(cached_at);
        CREATE TABLE IF NOT EXISTS simulation_scenarios (
            scenario_id TEXT PRIMARY KEY,
            user_id TEXT,
            name TEXT,
            description TEXT,
            proposed_holdings TEXT,
            current_holdings TEXT,
            backtest_result TEXT,
            is_nba_based INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        );
    ''')
    
    # Migration: Add new columns if they don't exist
    try:
        c.execute("ALTER TABLE portfolios ADD COLUMN industry TEXT DEFAULT 'Unknown'")
    except:
        pass
    try:
        c.execute("ALTER TABLE portfolios ADD COLUMN exchange TEXT DEFAULT 'Unknown'")
    except:
        pass
    try:
        c.execute("ALTER TABLE portfolios ADD COLUMN currency TEXT DEFAULT 'USD'")
    except:
        pass
    
    conn.commit()
    conn.close()

# ── Auth ──────────────────────────────────────────────────────────────────────
def signup(name, email, password, country, phone=None, occupation=None, experience=None):
    conn = _conn()
    c = conn.cursor()
    uid = f"WM-{str(uuid.uuid4())[:6].upper()}"
    try:
        c.execute(
            "INSERT INTO users VALUES (?,?,?,?,?,?,?,?,?,?)",
            (uid, name, email, _hash(password), country, phone, occupation, experience, "free", datetime.utcnow().isoformat())
        )
        conn.commit()
        return {"success": True, "user_id": uid}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()

def login(email, password):
    conn = _conn()
    c = conn.cursor()
    hashed = _hash(password)
    c.execute(
        "SELECT user_id, name, email, account_type, password_hash FROM users WHERE email=?",
        (email,)
    )
    row = c.fetchone()
    if row:
        stored_hash = row[4]
        if stored_hash == hashed:
            conn.close()
            return {"success": True, "user_id": row[0], "name": row[1], "email": row[2], "account_type": row[3]}
        else:
            conn.close()
            return {"success": False, "error": "Invalid email or password."}
    conn.close()
    return {"success": False, "error": "Invalid email or password."}

def get_user(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT user_id,name,email,country,phone,occupation,experience_level,account_type,created_at FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["user_id","name","email","country","phone","occupation","experience_level","account_type","created_at"]
        return dict(zip(keys, row))
    return None

# ── Risk Profile ──────────────────────────────────────────────────────────────
def save_risk_profile(user_id, risk_tolerance, investment_horizon, goals, liquidity_need, portfolio_size):
    conn = _conn()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO risk_profiles VALUES (?,?,?,?,?,?,?)",
              (user_id, risk_tolerance, investment_horizon, json.dumps(goals), liquidity_need, portfolio_size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_risk_profile(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT * FROM risk_profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["user_id","risk_tolerance","investment_horizon","goals","liquidity_need","portfolio_size","completed_at"]
    d = dict(zip(keys, row))
    try: d["goals"] = json.loads(d["goals"])
    except: pass
    return d

# ── Portfolio ─────────────────────────────────────────────────────────────────
def upsert_holding(user_id, ticker, quantity, avg_price, date_bought=None, metadata=None):
    """
    Insert or update a portfolio holding with enriched metadata.
    
    Args:
        user_id: User identifier
        ticker: Stock ticker symbol
        quantity: Number of shares
        avg_price: Average purchase price
        date_bought: Purchase date (optional)
        metadata: Dict with company_name, asset_type, sector, industry, exchange, currency
    """
    conn = _conn()
    c = conn.cursor()
    
    # Use metadata or defaults
    company_name = metadata.get("company_name", ticker) if metadata else ticker
    asset_type = metadata.get("asset_type", "Stock") if metadata else "Stock"
    sector = metadata.get("sector", "Unknown") if metadata else "Unknown"
    industry = metadata.get("industry", "Unknown") if metadata else "Unknown"
    exchange = metadata.get("exchange", "Unknown") if metadata else "Unknown"
    
    c.execute("DELETE FROM portfolios WHERE user_id=? AND ticker=?", (user_id, ticker))
    c.execute("""INSERT INTO portfolios 
        (entry_id, user_id, ticker, company_name, quantity, avg_price, asset_type, sector, industry, exchange, date_bought, added_at) 
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
              (str(uuid.uuid4())[:8], user_id, ticker, company_name, quantity, avg_price, 
               asset_type, sector, industry, exchange, date_bought, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def upsert_holding_legacy(user_id, ticker, company_name, quantity, avg_price, asset_type, sector, date_bought):
    """Legacy function for backward compatibility."""
    return upsert_holding(user_id, ticker, quantity, avg_price, date_bought, 
                         {"company_name": company_name, "asset_type": asset_type, "sector": sector})

def delete_holding(user_id, ticker):
    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM portfolios WHERE user_id=? AND ticker=?", (user_id, ticker))
    conn.commit()
    conn.close()

def get_portfolio(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT ticker, company_name, quantity, avg_price, asset_type, sector, industry, exchange, date_bought FROM portfolios WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{
        "ticker": r[0],
        "company_name": r[1],
        "quantity": float(r[2]) if r[2] is not None else 0.0,
        "avg_price": float(r[3]) if r[3] is not None else 0.0,
        "asset_type": r[4],
        "sector": r[5],
        "industry": r[6] if len(r) > 6 else "Unknown",
        "exchange": r[7] if len(r) > 7 else "Unknown",
        "date_bought": r[8] if len(r) > 8 else None
    } for r in rows]

# ── Alerts ────────────────────────────────────────────────────────────────────
def create_alert(user_id, message, alert_type="info"):
    conn = _conn()
    c = conn.cursor()
    c.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?)",
              (str(uuid.uuid4())[:8], user_id, message, alert_type, 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_alerts(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT alert_id,message,alert_type,is_read,created_at FROM alerts WHERE user_id=? ORDER BY created_at DESC LIMIT 30", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"alert_id": r[0], "message": r[1], "alert_type": r[2], "is_read": bool(r[3]), "created_at": r[4]} for r in rows]

def mark_read(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("UPDATE alerts SET is_read=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

# ── NBA History ───────────────────────────────────────────────────────────────
def save_nba(user_id, result: dict):
    conn = _conn()
    c = conn.cursor()
    
    # Handle next_best_action which can be string or dict
    nba_action = result.get("next_best_action", "")
    if isinstance(nba_action, dict):
        nba_action = json.dumps(nba_action)
    
    c.execute("INSERT INTO nba_history VALUES (?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4())[:8], user_id,
               result.get("market_insight",""), result.get("portfolio_impact",""),
               nba_action, result.get("confidence_score",0),
               json.dumps(result.get("flags",[])), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_nba_history(user_id, limit=10):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT rec_id,market_insight,portfolio_impact,next_best_action,confidence_score,flags,created_at FROM nba_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = {"rec_id": r[0],"market_insight": r[1],"portfolio_impact": r[2],"next_best_action": r[3],"confidence_score": r[4],"flags": r[5],"created_at": r[6]}
        try: d["flags"] = json.loads(d["flags"])
        except: pass
        result.append(d)
    return result

# ── Chat History ──────────────────────────────────────────────────────────────
def save_chat_message(user_id, role, content):
    conn = _conn()
    c = conn.cursor()
    c.execute("INSERT INTO chat_history VALUES (?,?,?,?,?)",
              (str(uuid.uuid4())[:8], user_id, role, content, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_chat_history(user_id, limit=20):
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT role,content,created_at FROM chat_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1], "created_at": r[2]} for r in reversed(rows)]

# ── Stock Analysis Cache ─────────────────────────────────────────────────────
CACHE_TTL_HOURS = 4

def get_cached_stock_analysis(user_id, ticker, ttl_hours: int = CACHE_TTL_HOURS):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT ai_analysis, personalized_context, generated_at FROM stock_analysis_cache 
        WHERE user_id=? AND ticker=? AND datetime(generated_at) > datetime('now', '-' || ? || ' hours')
    """, (user_id, ticker.upper(), ttl_hours))
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "ai_analysis": row[0],
            "personalized_context": json.loads(row[1]) if row[1] else None,
            "generated_at": row[2]
        }
    return None

def save_stock_analysis_cache(user_id, ticker, ai_analysis, personalized_context):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO stock_analysis_cache (cache_id, user_id, ticker, ai_analysis, personalized_context, generated_at)
        VALUES (?,?,?,?,?,?)
    """, (str(uuid.uuid4())[:8], user_id, ticker.upper(), ai_analysis, json.dumps(personalized_context), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def clear_stock_analysis_cache(user_id=None, ticker=None):
    conn = _conn()
    c = conn.cursor()
    if user_id and ticker:
        c.execute("DELETE FROM stock_analysis_cache WHERE user_id=? AND ticker=?", (user_id, ticker.upper()))
    elif user_id:
        c.execute("DELETE FROM stock_analysis_cache WHERE user_id=?", (user_id,))
    elif ticker:
        c.execute("DELETE FROM stock_analysis_cache WHERE ticker=?", (ticker.upper(),))
    else:
        c.execute("DELETE FROM stock_analysis_cache")
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

# ── Portfolio Price History ───────────────────────────────────────────────────
def save_price_history(user_id, ticker, date_str, open_price, high, low, close, volume):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        INSERT OR REPLACE INTO portfolio_price_history 
        (user_id, ticker, date, open, high, low, close, volume, created_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (user_id, ticker.upper(), date_str, open_price, high, low, close, volume, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def save_batch_price_history(user_id, ticker, price_data_list):
    conn = _conn()
    c = conn.cursor()
    created_at = datetime.utcnow().isoformat()
    for data in price_data_list:
        c.execute("""
            INSERT OR REPLACE INTO portfolio_price_history 
            (user_id, ticker, date, open, high, low, close, volume, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (user_id, ticker.upper(), data['date'], data['open'], data['high'], 
              data['low'], data['close'], data['volume'], created_at))
    conn.commit()
    conn.close()

def get_price_history(user_id, ticker, days=365):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT date, open, high, low, close, volume FROM portfolio_price_history 
        WHERE user_id=? AND ticker=? AND date >= date('now', '-' || ? || ' days')
        ORDER BY date ASC
    """, (user_id, ticker.upper(), days))
    rows = c.fetchall()
    conn.close()
    return [{"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rows]

def get_all_price_history(user_id, days=365):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT ticker, date, close FROM portfolio_price_history 
        WHERE user_id=? AND date >= date('now', '-' || ? || ' days')
        ORDER BY ticker, date ASC
    """, (user_id, days))
    rows = c.fetchall()
    conn.close()
    result = {}
    for r in rows:
        ticker = r[0]
        if ticker not in result:
            result[ticker] = []
        result[ticker].append({"date": r[1], "close": r[2]})
    return result

def get_portfolio_tickers_with_history(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT ticker FROM portfolio_price_history 
        WHERE user_id=? AND date >= date('now', '-365 days')
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_latest_price_date(user_id, ticker):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT MAX(date) FROM portfolio_price_history 
        WHERE user_id=? AND ticker=?
    """, (user_id, ticker.upper()))
    row = c.fetchone()
    conn.close()
    return row[0] if row and row[0] else None

def get_portfolio_prices_batch(tickers: list, period: str = "1d") -> dict:
    if not tickers:
        return {}
    
    try:
        import yfinance as yf
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            normalized_tickers = []
            for t in tickers:
                if not any(t.endswith(s) for s in ['.NS', '.BO', '.SI', '.SS', '.L', '.F', '.OL']):
                    try:
                        tick = yf.Ticker(t)
                        hist = tick.history(period=period)
                        if hist is None or hist.empty:
                            normalized_tickers.append(f"{t}.NS")
                        else:
                            normalized_tickers.append(t)
                    except:
                        normalized_tickers.append(f"{t}.NS")
                else:
                    normalized_tickers.append(t)
            
            tickers_str = " ".join(normalized_tickers)
            data = yf.download(tickers_str, period=period, group_by='ticker', progress=False)
            
            prices = {}
            for i, ticker in enumerate(tickers):
                norm_ticker = normalized_tickers[i]
                try:
                    if len(normalized_tickers) == 1:
                        price = float(data["Close"].iloc[-1])
                    else:
                        price = float(data[norm_ticker]["Close"].iloc[-1])
                    prices[ticker] = price
                except Exception:
                    prices[ticker] = None
            return prices
    except Exception as e:
        print(f"Batch price fetch failed: {e}")
        return {}


def get_cached_price_history(ticker: str, days: int = 365) -> list:
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT date, open, high, low, close, volume FROM stock_price_cache 
        WHERE ticker=? AND date >= date('now', '-' || ? || ' days')
        AND cached_at >= datetime('now', '-' || ? || ' hours')
        ORDER BY date ASC
    """, (ticker.upper(), days, 24))
    rows = c.fetchall()
    conn.close()
    return [{"date": r[0], "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in rows]


def cache_price_history(ticker: str, price_data: list):
    if not price_data:
        return
    conn = _conn()
    c = conn.cursor()
    cached_at = datetime.utcnow().isoformat()
    for data in price_data:
        try:
            c.execute("""
                INSERT OR REPLACE INTO stock_price_cache 
                (cache_id, ticker, date, open, high, low, close, volume, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                f"{ticker.upper()}_{data['date']}",
                ticker.upper(),
                data["date"],
                data["open"],
                data["high"],
                data["low"],
                data["close"],
                data["volume"],
                cached_at
            ))
        except Exception as e:
            print(f"Error caching price data for {ticker}: {e}")
    conn.commit()
    conn.close()


def cleanup_expired_cache():
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        DELETE FROM stock_price_cache 
        WHERE cached_at < datetime('now', '-24 hours')
    """)
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return deleted

# ── Simulation Scenarios ───────────────────────────────────────────────────────
def save_scenario(user_id, name, description, proposed_holdings, current_holdings, is_nba_based=False):
    conn = _conn()
    c = conn.cursor()
    scenario_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    c.execute("""
        INSERT INTO simulation_scenarios 
        (scenario_id, user_id, name, description, proposed_holdings, current_holdings, is_nba_based, created_at, updated_at)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, (scenario_id, user_id, name, description, json.dumps(proposed_holdings), json.dumps(current_holdings), 
          1 if is_nba_based else 0, now, now))
    conn.commit()
    conn.close()
    return scenario_id

def update_scenario_backtest(scenario_id, backtest_result):
    conn = _conn()
    c = conn.cursor()
    c.execute("UPDATE simulation_scenarios SET backtest_result=?, updated_at=? WHERE scenario_id=?",
              (json.dumps(backtest_result), datetime.utcnow().isoformat(), scenario_id))
    conn.commit()
    conn.close()

def get_scenarios(user_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT scenario_id, name, description, proposed_holdings, current_holdings, 
               backtest_result, is_nba_based, created_at, updated_at 
        FROM simulation_scenarios WHERE user_id=? ORDER BY created_at DESC
    """, (user_id,))
    rows = c.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "scenario_id": r[0],
            "name": r[1],
            "description": r[2],
            "proposed_holdings": json.loads(r[3]) if r[3] else [],
            "current_holdings": json.loads(r[4]) if r[4] else [],
            "backtest_result": json.loads(r[5]) if r[5] else None,
            "is_nba_based": bool(r[6]),
            "created_at": r[7],
            "updated_at": r[8]
        })
    return result

def get_scenario(user_id, scenario_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("""
        SELECT scenario_id, name, description, proposed_holdings, current_holdings, 
               backtest_result, is_nba_based, created_at, updated_at 
        FROM simulation_scenarios WHERE user_id=? AND scenario_id=?
    """, (user_id, scenario_id))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "scenario_id": row[0],
        "name": row[1],
        "description": row[2],
        "proposed_holdings": json.loads(row[3]) if row[3] else [],
        "current_holdings": json.loads(row[4]) if row[4] else [],
        "backtest_result": json.loads(row[5]) if row[5] else None,
        "is_nba_based": bool(row[6]),
        "created_at": row[7],
        "updated_at": row[8]
    }

def delete_scenario(user_id, scenario_id):
    conn = _conn()
    c = conn.cursor()
    c.execute("DELETE FROM simulation_scenarios WHERE user_id=? AND scenario_id=?", (user_id, scenario_id))
    conn.commit()
    conn.close()

def migrate_ticker_suffixes():
    import yfinance as yf
    import warnings
    conn = _conn()
    c = conn.cursor()
    c.execute("SELECT DISTINCT ticker FROM portfolios")
    tickers = [r[0] for r in c.fetchall()]
    updated = 0
    for ticker in tickers:
        if ticker in ["Cash", "USD", "EUR"] or any(ticker.endswith(s) for s in ['.NS', '.BO', '.SI', '.SS', '.L', '.F', '.OL', '.AX', '.TO']):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            try:
                tick = yf.Ticker(ticker)
                hist = tick.history(period="1d", timeout=5)
                if hist is None or hist.empty:
                    tick_ns = yf.Ticker(f"{ticker}.NS")
                    hist_ns = tick_ns.history(period="1d", timeout=5)
                    if hist_ns is not None and not hist_ns.empty:
                        c.execute("UPDATE portfolios SET ticker=? WHERE ticker=?", (f"{ticker}.NS", ticker))
                        c.execute("UPDATE portfolio_price_history SET ticker=? WHERE ticker=?", (f"{ticker}.NS", ticker))
                        updated += 1
            except:
                pass
    conn.commit()
    conn.close()
    print(f"Migrated {updated} tickers to include .NS suffix")
    return updated
