import ipaddress
import logging

import requests

logger = logging.getLogger(__name__)

# Successful lookups only - a failed lookup is retried next time it's seen.
_cache: dict[str, str] = {}


def is_public_ip(ip: str) -> bool:
    """True for internet-routable addresses; False for loopback, LAN, link-local and junk."""
    try:
        return ipaddress.ip_address(ip).is_global
    except ValueError:
        return False


def ip_country(ip: str) -> str:
    """Two-letter country code for `ip`, "LOCAL" for non-public addresses, "??" if the lookup fails."""
    if not ip:
        return "??"
    if not is_public_ip(ip):
        return "LOCAL"
    if ip in _cache:
        return _cache[ip]

    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
    except requests.RequestException as exc:
        logger.warning("Country lookup for %s failed: %s", ip, exc)
        return "??"
    if r.status_code != 200:
        logger.warning("Country lookup for %s failed: HTTP %s", ip, r.status_code)
        return "??"

    try:
        country = r.json().get("country")
    except ValueError:
        country = None
    if not country:
        logger.warning("Country lookup for %s returned no country", ip)
        return "??"
    _cache[ip] = country
    return country
