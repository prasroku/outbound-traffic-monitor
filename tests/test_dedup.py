"""Bug 3: an open connection was logged again every 5-second cycle."""

from collections.abc import Callable

import pytest

from monitor_script import select_new_connections


def test_select_new_connections_when_same_connections_seen_again_returns_none(make_conn: Callable) -> None:
    conns = [make_conn(port=443), make_conn(port=80, local_port=50001)]

    first, seen = select_new_connections(conns, set())
    second, seen = select_new_connections(conns, seen)

    assert len(first) == 2
    assert second == []


def test_select_new_connections_when_new_connection_opens_returns_only_it(make_conn: Callable) -> None:
    existing = make_conn(port=443)
    _, seen = select_new_connections([existing], set())

    opened = make_conn(ip="1.1.1.1", local_port=50002)
    new, _ = select_new_connections([existing, opened], seen)

    assert new == [opened]


def test_select_new_connections_when_connection_closes_and_reopens_counts_it_again(make_conn: Callable) -> None:
    conn = make_conn()
    _, seen = select_new_connections([conn], set())
    _, seen = select_new_connections([], seen)

    new, _ = select_new_connections([conn], seen)

    assert new == [conn]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"status": "TIME_WAIT"},
        {"pid": None},
        {"ip": "127.0.0.1"},
        {"ip": "192.168.1.20"},
        {"ip": "::1"},
    ],
    ids=["not-established", "no-pid", "loopback", "lan", "ipv6-loopback"],
)
def test_select_new_connections_when_not_outbound_internet_ignores_it(make_conn: Callable, kwargs: dict) -> None:
    new, seen = select_new_connections([make_conn(**kwargs)], set())

    assert new == []
    assert seen == set()
