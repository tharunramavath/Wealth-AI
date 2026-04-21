import sqlite3
import os

DB_PATH = "data/monitoring.db"

def log_prediction(client_id, latency_ms, confidence, flags, recommendation):
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS predictions (
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            client_id TEXT,
            latency_ms REAL,
            confidence REAL,
            flags_count INTEGER,
            is_compliant BOOLEAN,
            recommendation TEXT
        )
    ''')
    is_compliant = len(flags) == 0
    cursor.execute('''
        INSERT INTO predictions (client_id, latency_ms, confidence, flags_count, is_compliant, recommendation)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (client_id, latency_ms, confidence, len(flags), is_compliant, recommendation))
    conn.commit()
    conn.close()

def get_monitoring_metrics():
    """Retrieve telemetry metrics for the dashboard."""
    if not os.path.exists(DB_PATH):
        return {"total_predictions": 0, "avg_latency_ms": 0, "avg_confidence": 0, "compliance_rate": 1.0}
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT COUNT(*), AVG(latency_ms), AVG(confidence), AVG(is_compliant) FROM predictions")
        row = cursor.fetchone()
        count = row[0] or 0
        avg_lat = row[1] or 0.0
        avg_conf = row[2] or 0.0
        comp_rate = row[3] or 1.0
    except sqlite3.OperationalError:
        count, avg_lat, avg_conf, comp_rate = 0, 0, 0, 1.0
        
    conn.close()
    return {
        "total_predictions": count,
        "avg_latency_ms": avg_lat,
        "avg_confidence": avg_conf,
        "compliance_rate": comp_rate
    }
