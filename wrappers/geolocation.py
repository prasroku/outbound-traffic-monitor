import requests


def ip_country(ip):
    try:
        if not ip:
            return "??"
        r = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5)
        return r.json().get("country", "??")
    except Exception:
        return "??"
