"""Bug 2: there was no way to train the IsolationForest, so the monitor never left [LEARN] mode."""

import os
import sys
from collections.abc import Callable
from unittest.mock import patch

import pytest

from modelling import model_tools
from traffic_guard import cli


def test_train_command_when_enough_samples_saves_loadable_model(add_traffic: Callable[..., None]) -> None:
    add_traffic("FI", count=60)

    with patch.object(sys, "argv", ["main.py", "train"]):
        cli.main()

    assert os.path.exists(os.environ["TRAFFIC_MODEL"])
    assert model_tools.load_model() is not None


def test_train_command_when_too_few_samples_saves_nothing(
    add_traffic: Callable[..., None], capsys: pytest.CaptureFixture[str]
) -> None:
    add_traffic("FI", count=10)

    with patch.object(sys, "argv", ["main.py", "train"]):
        cli.main()

    assert not os.path.exists(os.environ["TRAFFIC_MODEL"])
    assert "Not enough data" in capsys.readouterr().out
