import sqlite3

from . import db_utils
from .baseline import pct_by_country

RISK_COUNTRIES = {"CN", "RU", "IR", "KP"}


def check_distribution(
    window_from=None, window_to=None, global_thresh=30.0, risk_thresh=5.0, use_baseline=False, sigma=3.0
):
    db_utils.ensure_schema()
    rows = db_utils.fetch_rows(window_from, window_to)
    if not rows:
        print("[!] No data in given window")
        return

    countries = [c or "??" for _, c in rows]
    dist = pct_by_country(countries)

    conn = sqlite3.connect(db_utils.db_file())
    cur = conn.cursor()
    cur.execute("SELECT country, pct_avg, pct_std, samples FROM country_baseline")
    base = {c: (avg, std, n) for c, avg, std, n in cur.fetchall()}
    conn.close()

    flagged = False
    for c, pct in sorted(dist.items(), key=lambda x: x[1], reverse=True):
        reasons = []
        if pct > global_thresh:
            reasons.append(f"GLOBAL>{global_thresh}%")
            db_utils.insert_alert(c, pct, "GLOBAL_THRESHOLD", global_thresh, window_from, window_to)
        if c in RISK_COUNTRIES and pct > risk_thresh:
            reasons.append(f"RISK>{risk_thresh}%")
            db_utils.insert_alert(c, pct, "RISK_COUNTRY", risk_thresh, window_from, window_to)
        if use_baseline and c in base and base[c][2] >= 3:
            avg, std, _ = base[c]
            limit = avg + sigma * std
            if pct > limit:
                reasons.append(f"BASE>{limit:.2f}%")
                db_utils.insert_alert(c, pct, "BASELINE_SIGMA", limit, window_from, window_to)

        tag = " [RED FLAG]" if reasons else ""
        why = f" <- {', '.join(reasons)}" if reasons else ""
        print(f"{c:>3}: {pct:.2f}%{tag}{why}")
        if reasons:
            flagged = True

    if not flagged:
        print("[✓] All countries under thresholds.")
