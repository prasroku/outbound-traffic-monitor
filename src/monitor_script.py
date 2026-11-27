import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

import psutil

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from modelling.model_tools import load_model  # noqa: E402
from paths import db_file  # noqa: E402
from wrappers.geolocation import ip_country, is_public_ip  # noqa: E402

RISK_COUNTRIES = {"CN", "RU", "IR", "KP"}


# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(db_file())
    cur = conn.cursor()
    cur.execute("""
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
    """)
    conn.commit()
    conn.close()


def insert_row(row):
    conn = sqlite3.connect(db_file())
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
def process_name(pid: int) -> str | None:
    """Name of the process, "unknown" if we may not read it, None if it has already exited."""
    try:
        return psutil.Process(pid).name()
    except psutil.NoSuchProcess:
        return None
    except psutil.AccessDenied:
        return "unknown"


def extract_features(conn) -> dict | None:
    """Row for the traffic log, or None if the owning process exited mid-scan."""
    pname = process_name(conn.pid) if conn.pid else "unknown"
    if pname is None:
        return None
    ip = getattr(conn.raddr, "ip", "")
    port = getattr(conn.raddr, "port", 0)
    country = ip_country(ip) if ip else "??"
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pid": conn.pid,
        "process_name": pname,
        "ip": ip,
        "port": port,
        "country": country,
        "risk_flag": int(country in RISK_COUNTRIES),
    }


def connection_key(conn) -> tuple:
    return (conn.pid, conn.laddr.port if conn.laddr else 0, conn.raddr.ip, conn.raddr.port)


def select_new_connections(conns, seen: set) -> tuple[list, set]:
    """Established outbound internet connections that weren't open last cycle.

    Returns the new connections and the set of keys open right now, which becomes
    `seen` for the next cycle - so a connection that closes and reopens counts again.
    """
    current = {
        connection_key(c): c
        for c in conns
        if c.status == "ESTABLISHED" and c.raddr and c.pid and is_public_ip(c.raddr.ip)
    }
    new = [c for key, c in current.items() if key not in seen]
    return new, set(current)


# --- MONITOR LOOP ---
def monitor():
    init_db()
    model = load_model()
    seen = set()

    print("[*] Monitoring outbound traffic...\n")

    while True:
        try:
            new_conns, seen = select_new_connections(psutil.net_connections(kind="inet"), seen)
            for c in new_conns:
                feat = extract_features(c)
                if feat is None:
                    continue
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
