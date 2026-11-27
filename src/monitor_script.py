import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import psutil

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modelling.model_tools import load_model
from wrappers.geolocation import ip_country

DB_FILE = "traffic.db"
RISK_COUNTRIES = {"CN", "RU", "IR", "KP"}


# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS traffic_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        pid INTEGER,
        process_name TEXT,
        ip TEXT,
        port INTEGER,
        country TEXT,
        risk_flag INTEGER
    )
    """
    )
    conn.commit()
    conn.close()


def insert_row(row):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute(
        """
    INSERT INTO traffic_log (timestamp,pid,process_name,ip,port,country,risk_flag)
    VALUES (?,?,?,?,?,?,?)
    """,
        (row["timestamp"], row["pid"], row["process_name"], row["ip"], row["port"], row["country"], row["risk_flag"]),
    )
    conn.commit()
    conn.close()


# --- FEATURES ---
def extract_features(conn):
    ip = getattr(conn.raddr, "ip", "")
    port = getattr(conn.raddr, "port", 0)
    country = ip_country(ip) if ip else "??"
    pname = psutil.Process(conn.pid).name() if conn.pid else "unknown"
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": conn.pid,
        "process_name": pname,
        "ip": ip,
        "port": port,
        "country": country,
        "risk_flag": int(country in RISK_COUNTRIES),
    }


# --- MONITOR LOOP ---
def monitor():
    init_db()
    model = load_model()

    print("[*] Monitoring outbound traffic...\n")

    while True:
        try:
            conns = psutil.net_connections(kind="inet")
            for c in conns:
                if c.status == "ESTABLISHED" and c.raddr and c.pid:
                    feat = extract_features(c)
                    insert_row(feat)

                    if model:
                        import numpy as np

                        X = np.array([[feat["port"], feat["risk_flag"]]])
                        score = -model.score_samples(X)[0]
                        if score > 0.7 or feat["risk_flag"]:
                            print(f"[ALERT] Suspicious traffic: {feat}")
                    else:
                        print(f"[LEARN] Stored: {feat}")

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n[!] Stopping monitor...")
            break


if __name__ == "__main__":
    monitor()
