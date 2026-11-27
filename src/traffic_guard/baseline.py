import math
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone

from . import db_utils


def chunk_by_day(rows):
    buckets = defaultdict(list)
    for ts, country in rows:
        buckets[(ts or "")[:10]].append(country or "??")
    return buckets


def pct_by_country(lst):
    total = len(lst)
    if total == 0:
        return {}
    counts = defaultdict(int)
    for c in lst:
        counts[c] += 1
    return {c: (n / total) * 100.0 for c, n in counts.items()}


def learn_baseline():
    db_utils.ensure_schema()
    rows = db_utils.fetch_rows()
    if not rows:
        print("[!] No traffic data found")
        return

    by_day = chunk_by_day(rows)
    country_to_pctlist = defaultdict(list)
    for _, c_list in by_day.items():
        pct_map = pct_by_country(c_list)
        for c, pct in pct_map.items():
            country_to_pctlist[c].append(pct)

    # Store baseline
    conn = sqlite3.connect(db_utils.db_file())
    cur = conn.cursor()
    now_iso = f"{datetime.now(timezone.utc).isoformat()}Z"
    for c, plist in country_to_pctlist.items():
        avg = sum(plist) / len(plist)
        std = math.sqrt(sum((x - avg) ** 2 for x in plist) / len(plist))
        cur.execute(
            """
          INSERT INTO country_baseline(country, pct_avg, pct_std, samples, updated_at)
          VALUES (?,?,?,?,?)
          ON CONFLICT(country) DO UPDATE SET
            pct_avg=excluded.pct_avg,
            pct_std=excluded.pct_std,
            samples=excluded.samples,
            updated_at=excluded.updated_at
        """,
            (c, avg, std, len(plist), now_iso),
        )
    conn.commit()
    conn.close()
    print("[*] Baseline updated.")
