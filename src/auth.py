import sqlite3
import hashlib
import os
import json
import uuid
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/platform.db"

def _hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def _get_conn():
    os.makedirs("data", exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_user_db():
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
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
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS risk_profiles (
        user_id TEXT PRIMARY KEY,
        risk_tolerance TEXT,
        investment_horizon TEXT,
        goals TEXT,
        liquidity_need TEXT,
        portfolio_size TEXT,
        completed_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolios (
        entry_id TEXT PRIMARY KEY,
        user_id TEXT,
        ticker TEXT,
        quantity REAL,
        avg_price REAL,
        asset_type TEXT,
        sector TEXT,
        added_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS alerts (
        alert_id TEXT PRIMARY KEY,
        user_id TEXT,
        message TEXT,
        alert_type TEXT,
        is_read INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS nba_history (
        rec_id TEXT PRIMARY KEY,
        user_id TEXT,
        market_insight TEXT,
        portfolio_impact TEXT,
        next_best_action TEXT,
        confidence_score REAL,
        flags TEXT,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

def signup_user(name, email, password, country, phone=None, occupation=None, experience_level=None):
    init_user_db()
    conn = _get_conn()
    c = conn.cursor()
    user_id = str(uuid.uuid4())[:8].upper()
    try:
        c.execute('''INSERT INTO users (user_id,name,email,password_hash,country,phone,occupation,experience_level,account_type,created_at)
                     VALUES (?,?,?,?,?,?,?,?,?,?)''',
                  (user_id, name, email, _hash_password(password), country, phone, occupation, experience_level, 'free', datetime.utcnow().isoformat()))
        conn.commit()
        return {"success": True, "user_id": user_id}
    except sqlite3.IntegrityError:
        return {"success": False, "error": "Email already registered."}
    finally:
        conn.close()

def login_user(email, password):
    init_user_db()
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id, name, email, account_type FROM users WHERE email=? AND password_hash=?",
              (email, _hash_password(password)))
    row = c.fetchone()
    conn.close()
    if row:
        return {"success": True, "user_id": row[0], "name": row[1], "email": row[2], "account_type": row[3]}
    return {"success": False, "error": "Invalid email or password."}

def get_user(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["user_id","name","email","password_hash","country","phone","occupation","experience_level","account_type","created_at"]
        return dict(zip(keys, row))
    return None

def save_risk_profile(user_id, risk_tolerance, investment_horizon, goals, liquidity_need, portfolio_size):
    conn = _get_conn()
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO risk_profiles VALUES (?,?,?,?,?,?,?)''',
              (user_id, risk_tolerance, investment_horizon, json.dumps(goals), liquidity_need, portfolio_size, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_risk_profile(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM risk_profiles WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        keys = ["user_id","risk_tolerance","investment_horizon","goals","liquidity_need","portfolio_size","completed_at"]
        d = dict(zip(keys, row))
        try: d["goals"] = json.loads(d["goals"])
        except: pass
        return d
    return None

def save_portfolio_entry(user_id, ticker, quantity, avg_price, asset_type, sector):
    conn = _get_conn()
    c = conn.cursor()
    entry_id = str(uuid.uuid4())[:8]
    c.execute("DELETE FROM portfolios WHERE user_id=? AND ticker=?", (user_id, ticker))
    c.execute('''INSERT INTO portfolios VALUES (?,?,?,?,?,?,?,?)''',
              (entry_id, user_id, ticker, quantity, avg_price, asset_type, sector, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_portfolio(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT ticker,quantity,avg_price,asset_type,sector FROM portfolios WHERE user_id=?", (user_id,))
    rows = c.fetchall()
    conn.close()
    return [{"ticker": r[0], "quantity": r[1], "avg_price": r[2], "asset_type": r[3], "sector": r[4]} for r in rows]

def create_alert(user_id, message, alert_type="info"):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?)",
              (str(uuid.uuid4())[:8], user_id, message, alert_type, 0, datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_alerts(user_id, unread_only=False):
    conn = _get_conn()
    c = conn.cursor()
    if unread_only:
        c.execute("SELECT * FROM alerts WHERE user_id=? AND is_read=0 ORDER BY created_at DESC", (user_id,))
    else:
        c.execute("SELECT * FROM alerts WHERE user_id=? ORDER BY created_at DESC LIMIT 20", (user_id,))
    rows = c.fetchall()
    conn.close()
    keys = ["alert_id","user_id","message","alert_type","is_read","created_at"]
    return [dict(zip(keys, r)) for r in rows]

def mark_alerts_read(user_id):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("UPDATE alerts SET is_read=1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def save_nba_record(user_id, result: dict):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("INSERT INTO nba_history VALUES (?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4())[:8], user_id,
               result.get("market_insight",""), result.get("portfolio_impact",""),
               result.get("next_best_action",""), result.get("confidence_score",0),
               json.dumps(result.get("flags",[])), datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_nba_history(user_id, limit=5):
    conn = _get_conn()
    c = conn.cursor()
    c.execute("SELECT * FROM nba_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?", (user_id, limit))
    rows = c.fetchall()
    conn.close()
    keys = ["rec_id","user_id","market_insight","portfolio_impact","next_best_action","confidence_score","flags","created_at"]
    result = []
    for r in rows:
        d = dict(zip(keys, r))
        try: d["flags"] = json.loads(d["flags"])
        except: pass
        result.append(d)
    return result
