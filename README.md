# outbound-traffic-monitor

A small tool that watches which processes on my machine are talking to the
internet, works out which country each connection goes to, and flags anything
that looks unusual. Everything stays local in a SQLite file.

## How it works

1. **Capture** (`src/monitor_script.py`): every 5 seconds, list established
   outbound connections to public IPs with `psutil`, find the owning process,
   look up the remote IP's country via [ipinfo.io](https://ipinfo.io), and log
   the row to `traffic.db`. A connection is logged once when it opens, not on
   every cycle it stays open. Loopback and LAN traffic is skipped. Connections
   to a small set of high-risk countries (`CN`, `RU`, `IR`, `KP`) get a risk
   flag.
2. **Anomaly scoring** (`modelling/model_tools.py`): an `IsolationForest`
   trained on `(port, risk_flag)` scores each new connection. Until you run
   `main.py train`, the monitor just logs (`[LEARN]` mode).
3. **Baseline + checks** (`src/traffic_guard/`): a CLI that learns each country's
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
│   ├── main.py             # CLI entry point (learn / train / check)
│   ├── visualize.py        # matplotlib charts
│   └── traffic_guard/
│       ├── cli.py          # argument parsing, --window 24h / 7d
│       ├── baseline.py     # per-country daily share, mean + std
│       ├── checking.py     # threshold and sigma checks, writes alerts
│       └── db_utils.py     # schema + queries
├── modelling/
│   └── model_tools.py      # IsolationForest train / load
├── wrappers/
│   └── geolocation.py      # ipinfo.io country lookup, cached, skips non-public IPs
├── tests/                  # pytest suite
├── paths.py                # where traffic.db and baseline.pkl live
├── requirements.txt
└── requirements-dev.txt
```

`traffic.db` and `baseline.pkl` live in the project root by default, whichever
directory you run from. Set `TRAFFIC_DB` / `TRAFFIC_MODEL` to put them
somewhere else.

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

# 2. train the anomaly model (needs 50+ captured connections), then restart the monitor
.venv\Scripts\python.exe src\main.py train

# 3. learn the per-country baseline from what's been captured
.venv\Scripts\python.exe src\main.py learn

# 4. check the last 24 hours (or 7d, etc.)
.venv\Scripts\python.exe src\main.py check --window 24h --use-baseline

# 5. charts
.venv\Scripts\python.exe src\visualize.py
```

Seeing every process's connections may need an elevated terminal. Failed
country lookups (offline, rate limited) are logged as warnings and recorded
as `??`.

## Tests

```
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m pytest tests
```

The tests use a temporary database and mock the ipinfo.io calls, so they
don't touch your real `traffic.db` or the network.

## Privacy

`traffic.db` and any trained `*.pkl` model are gitignored. They contain your
real connection history (remote IPs, process names, timestamps), so don't
commit or share them. Each public IP the monitor sees is also sent to
ipinfo.io for the country lookup, once per run.

## Known issues

- Running `check`, `learn` or `train` before the monitor has ever run fails
  with `No table traffic_log found`. Run the monitor first.
