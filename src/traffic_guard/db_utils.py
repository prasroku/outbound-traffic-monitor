import sqlite3
from datetime import datetime

from paths import db_file


def ensure_schema():
    conn = sqlite3.connect(db_file())
    cur = conn.cursor()
    cur.execute("""
      CREATE TABLE IF NOT EXISTS country_baseline (
        country TEXT PRIMARY KEY,
        pct_avg REAL NOT NULL,
        pct_std REAL NOT NULL,
        samples INTEGER NOT NULL,
        updated_at TEXT NOT NULL
      );
    """)
    cur.execute("""
      CREATE TABLE IF NOT EXISTS alert_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        country TEXT NOT NULL,
        percent REAL NOT NULL,
        reason TEXT NOT NULL,
        threshold REAL,
        window_from TEXT,
        window_to TEXT
      );
    """)
    conn.commit()
    conn.close()


def fetch_rows(time_from=None, time_to=None):
    conn = sqlite3.connect(db_file())
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='traffic_log';")
    if not cur.fetchone():
        conn.close()
        raise RuntimeError("No table traffic_log found")

    if time_from and time_to:
        cur.execute(
            "SELECT timestamp, country FROM traffic_log WHERE timestamp>=? AND timestamp<=?", (time_from, time_to)
        )
    else:
        cur.execute("SELECT timestamp, country FROM traffic_log")

    rows = cur.fetchall()
    conn.close()
    return rows


def insert_alert(country, percent, reason, threshold, win_from, win_to):
    ts_iso = f"{datetime.utcnow().isoformat()}Z"
    conn = sqlite3.connect(db_file())
    cur = conn.cursor()
    cur.execute(
        """
      INSERT INTO alert_log(ts, country, percent, reason, threshold, window_from, window_to)
      VALUES (?,?,?,?,?,?,?)
    """,
        (ts_iso, country, percent, reason, threshold, win_from, win_to),
    )
    conn.commit()
    conn.close()
