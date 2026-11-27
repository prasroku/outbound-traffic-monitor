# outbound-traffic-monitor

A small tool that watches which processes on my machine are talking to the
internet, works out which country each connection goes to, and flags anything
that looks unusual. Everything stays local in a SQLite file.

## How it works

1. **Capture** (`src/monitor_script.py`): every 5 seconds, list established
   outbound connections with `psutil`, find the owning process, look up the
   remote IP's country via [ipinfo.io](https://ipinfo.io), and log the row to
   `traffic.db`. Connections to a small set of high-risk countries
   (`CN`, `RU`, `IR`, `KP`) get a risk flag.
2. **Anomaly scoring** (`modelling/model_tools.py`): an `IsolationForest`
   trained on `(port, risk_flag)` scores each new connection. If no model has
   been trained yet, the monitor just logs (`[LEARN]` mode).
3. **Baseline + checks** (`src/llm_guard/`): a CLI that learns each country's
   normal daily share of traffic (mean and standard deviation), then checks a
   time window against three rules:
   - a country takes more than `--global-thresh` % of all traffic (default 30)
   - a risk country takes more than `--risk-thresh` % (default 5)
   - with `--use-baseline`, a country exceeds its normal share by more than
     `--sigma` standard deviations (default 3; needs 3+ days of history)

   Every breach is written to an `alert_log` table.
4. **Charts** (`src/visualize.py`): pie and bar charts of connections per
   country.

## Project layout

```
outbound-traffic-monitor/
├── src/
│   ├── monitor_script.py   # capture loop
│   ├── main.py             # CLI entry point (learn / check)
│   ├── visualize.py        # matplotlib charts
│   └── llm_guard/
│       ├── cli.py          # argument parsing, --window 24h / 7d
│       ├── baseline.py     # per-country daily share, mean + std
│       ├── checking.py     # threshold and sigma checks, writes alerts
│       └── db_utils.py     # schema + queries
├── modelling/
│   └── model_tools.py      # IsolationForest train / load
├── wrappers/
│   └── geolocation.py      # ipinfo.io country lookup
└── requirements.txt
```

## Setup

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Also needs `numpy` (pulled in by scikit-learn).

## Running it

From the project root:

```
# 1. capture traffic (Ctrl+C to stop)
.venv\Scripts\python.exe src\monitor_script.py

# 2. learn the per-country baseline from what's been captured
.venv\Scripts\python.exe src\main.py learn

# 3. check the last 24 hours (or 7d, etc.)
.venv\Scripts\python.exe src\main.py check --window 24h --use-baseline

# 4. charts
.venv\Scripts\python.exe src\visualize.py
```

Seeing every process's connections may need an elevated terminal.

## Privacy

`traffic.db` and any trained `*.pkl` model are gitignored. They contain your
real connection history (remote IPs, process names, timestamps), so don't
commit or share them. Every remote IP the monitor sees is also sent to
ipinfo.io for the country lookup.

## Known issues

Work in progress. Things I know are broken or rough:

- **Database path isn't consistent.** `monitor_script.py` and `model_tools.py`
  use `traffic.db` relative to the current directory, `visualize.py` uses the
  project root, and `llm_guard/db_utils.py` resolves to `src/traffic.db`. The
  CLI can end up reading a different (empty) database from the one the
  monitor writes.
- **The model is never trained.** Nothing calls `train_model()`, so the
  monitor stays in `[LEARN]` mode and the IsolationForest alerts never fire.
- **Connections are re-logged every 5 seconds** while they stay open, which
  inflates long-lived connections in the country percentages.
- **Every connection triggers an ipinfo.io lookup**, including private and
  loopback IPs, with no caching, so the free rate limit runs out quickly.
  Lookup failures are silently recorded as `??`.
- **A process exiting mid-scan crashes the monitor** (`psutil.NoSuchProcess`
  is not handled).
- **`llm_guard` is a misleading name** - there's no LLM involved. It'll be
  renamed.
