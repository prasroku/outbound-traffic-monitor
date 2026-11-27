"""Bug 5: a process exiting between net_connections() and Process() crashed the monitor."""

from collections.abc import Callable
from unittest.mock import MagicMock, patch

import psutil

import monitor_script


def test_extract_features_when_process_exited_returns_none(make_conn: Callable) -> None:
    with (
        patch.object(monitor_script.psutil, "Process", side_effect=psutil.NoSuchProcess(1234)),
        patch.object(monitor_script, "ip_country", return_value="FI") as lookup,
    ):
        assert monitor_script.extract_features(make_conn()) is None
    lookup.assert_not_called()


def test_extract_features_when_access_denied_keeps_row_with_unknown_name(make_conn: Callable) -> None:
    proc = MagicMock()
    proc.name.side_effect = psutil.AccessDenied(1234)
    with (
        patch.object(monitor_script.psutil, "Process", return_value=proc),
        patch.object(monitor_script, "ip_country", return_value="FI"),
    ):
        feat = monitor_script.extract_features(make_conn())

    assert feat is not None
    assert feat["process_name"] == "unknown"
    assert feat["country"] == "FI"
