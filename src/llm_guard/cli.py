import argparse
from datetime import datetime, timedelta, timezone

from . import baseline, checking


def parse_window(win_str):
    if not win_str:
        return None, None
    now = datetime.now(timezone.utc)
    unit = win_str[-1].lower()
    val = int(win_str[:-1])
    if unit == "h":
        delta = timedelta(hours=val)
    elif unit == "d":
        delta = timedelta(days=val)
    else:
        raise ValueError("Use h/d suffix (e.g., 24h, 7d)")
    return f"{(now - delta).isoformat()}Z", f"{now.isoformat()}Z"


def main():
    p = argparse.ArgumentParser("LLM Guard")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("learn", help="Update baseline from historical data")
    c = sub.add_parser("check", help="Check distribution against thresholds")
    c.add_argument("--window", default="24h", help="e.g., 24h, 7d")
    c.add_argument("--global-thresh", type=float, default=30.0)
    c.add_argument("--risk-thresh", type=float, default=5.0)
    c.add_argument("--use-baseline", action="store_true")
    c.add_argument("--sigma", type=float, default=3.0)

    args = p.parse_args()
    if args.cmd == "learn":
        baseline.learn_baseline()
    elif args.cmd == "check":
        f, t = parse_window(args.window)
        checking.check_distribution(f, t, args.global_thresh, args.risk_thresh, args.use_baseline, args.sigma)
