"""Bug 1: the monitor, the CLI, the model and the charts must all use the same database."""

import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import visualize
from modelling import model_tools
from traffic_guard import cli, db_utils


def test_db_readers_when_monitor_writes_see_same_rows(add_traffic: Callable[..., None]) -> None:
    add_traffic("FI", count=2)

    assert [country for _, country in db_utils.fetch_rows()] == ["FI", "FI"]
    assert visualize.get_country_counts() == [("FI", 2)]
    assert len(model_tools.load_samples()) == 2


def test_cli_check_when_one_country_dominates_writes_alert_to_monitor_db(
    traffic_db: Path, add_traffic: Callable[..., None]
) -> None:
    add_traffic("FI", count=9)
    add_traffic("SE", count=1)

    with patch.object(sys, "argv", ["main.py", "check", "--window", "24h"]):
        cli.main()

    with sqlite3.connect(traffic_db) as conn:
        alerts = conn.execute("SELECT country, reason FROM alert_log").fetchall()
    assert ("FI", "GLOBAL_THRESHOLD") in alerts
