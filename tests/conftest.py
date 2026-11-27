import sys
from collections import namedtuple
from collections.abc import Callable, Iterator
from datetime import datetime, timezone
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
for path in (PROJECT_ROOT, PROJECT_ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import monitor_script  # noqa: E402
from wrappers import geolocation  # noqa: E402

Addr = namedtuple("Addr", ["ip", "port"])
Conn = namedtuple("Conn", ["status", "laddr", "raddr", "pid"])


@pytest.fixture
def traffic_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every module at an empty temp database, and run from a temp cwd so nothing touches the real one."""
    db = tmp_path / "traffic.db"
    monkeypatch.setenv("TRAFFIC_DB", str(db))
    monkeypatch.setenv("TRAFFIC_MODEL", str(tmp_path / "baseline.pkl"))
    monkeypatch.chdir(tmp_path)
    monitor_script.init_db()
    return db


@pytest.fixture
def add_traffic(traffic_db: Path) -> Callable[..., None]:
    """Insert `count` traffic rows for `country`, timestamped now."""

    def _add(country: str, count: int = 1, port: int = 443, risk_flag: int = 0) -> None:
        for _ in range(count):
            monitor_script.insert_row(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "pid": 1234,
                    "process_name": "test.exe",
                    "ip": "8.8.8.8",
                    "port": port,
                    "country": country,
                    "risk_flag": risk_flag,
                }
            )

    return _add


@pytest.fixture
def make_conn() -> Callable[..., Conn]:
    """Build a fake psutil connection."""

    def _make(
        ip: str = "8.8.8.8", port: int = 443, pid: int = 1234, local_port: int = 50000, status: str = "ESTABLISHED"
    ) -> Conn:
        return Conn(status=status, laddr=Addr("10.0.0.2", local_port), raddr=Addr(ip, port), pid=pid)

    return _make


@pytest.fixture(autouse=True)
def clear_geo_cache() -> Iterator[None]:
    """The country cache is module-level; keep tests independent."""
    geolocation._cache.clear()
    yield
    geolocation._cache.clear()
