"""Single place that decides where the database and trained model live.

Defaults to the project root, so every script finds the same files no matter
which directory it's started from. Override with TRAFFIC_DB / TRAFFIC_MODEL.
"""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def db_file() -> Path:
    return Path(os.environ.get("TRAFFIC_DB", PROJECT_ROOT / "traffic.db"))


def model_file() -> Path:
    return Path(os.environ.get("TRAFFIC_MODEL", PROJECT_ROOT / "baseline.pkl"))
