"""Bug 4: every connection hit ipinfo.io (even LAN IPs), nothing was cached, and failures were silently hidden."""

import logging
from unittest.mock import MagicMock, patch

import pytest
import requests

from wrappers import geolocation


def _response(status: int = 200, country: str = "FI") -> MagicMock:
    resp = MagicMock(status_code=status)
    resp.json.return_value = {"country": country} if status == 200 else {"error": "rate limited"}
    return resp


@pytest.mark.parametrize("ip", ["127.0.0.1", "10.1.2.3", "192.168.0.5", "172.16.0.1", "169.254.1.1", "::1", "fe80::1"])
def test_ip_country_when_ip_not_public_returns_local_without_request(ip: str) -> None:
    with patch.object(geolocation.requests, "get") as get:
        assert geolocation.ip_country(ip) == "LOCAL"
    get.assert_not_called()


def test_ip_country_when_same_ip_looked_up_twice_requests_once() -> None:
    with patch.object(geolocation.requests, "get", return_value=_response(country="DE")) as get:
        assert geolocation.ip_country("8.8.8.8") == "DE"
        assert geolocation.ip_country("8.8.8.8") == "DE"
    assert get.call_count == 1


def test_ip_country_when_request_fails_logs_warning_and_retries_next_time(caplog: pytest.LogCaptureFixture) -> None:
    with patch.object(geolocation.requests, "get", side_effect=requests.ConnectionError("offline")):
        with caplog.at_level(logging.WARNING):
            assert geolocation.ip_country("8.8.8.8") == "??"
    assert "8.8.8.8" in caplog.text

    with patch.object(geolocation.requests, "get", return_value=_response(country="US")) as get:
        assert geolocation.ip_country("8.8.8.8") == "US"
    assert get.call_count == 1


def test_ip_country_when_rate_limited_logs_warning_and_returns_unknown(caplog: pytest.LogCaptureFixture) -> None:
    with patch.object(geolocation.requests, "get", return_value=_response(status=429)):
        with caplog.at_level(logging.WARNING):
            assert geolocation.ip_country("8.8.4.4") == "??"
    assert "429" in caplog.text
