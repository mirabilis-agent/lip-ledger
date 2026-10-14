"""Read-only helpers for Kalshi's public Weather Index (the settlement source of the hourly temperature markets).

Endpoints used (no API key): GET /live_data/weather/{city} (minute points, optional per-station readings) and /live_data/weather/{city}/calibrations.
The index is the equal-weight mean of 5-8 ASOS one-minute station temperatures. The stations report whole degrees Celsius, so the index moves on a lattice of
1.8 / n_stations degrees F (0.225 F for the 8-station NYC index, 0.36 F for the 5-station cities).
"""
from __future__ import annotations
import json
import re
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES_CITY = {"KXTEMPNYCHS": "nyc", "KXTEMPLAXHS": "la-coastal", "KXTEMPCHIHS": "chicago", "KXTEMPMIAH": "miami"}


def _get(path, params=None, timeout=20):
    url = BASE + path + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": "lip-ledger-windex/0.4 (read-only research tool)"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def cities():
    """Supported city ids (the API lists them in its error message for an unknown city)."""
    try:
        _get("/live_data/weather/__list__", {"last_sec": 60})
    except urllib.error.HTTPError as e:
        m = re.search(r"supported cities: \[([^\]]+)\]", e.read().decode())
        if m:
            return [c.strip() for c in m.group(1).split(",")]
    return []


def index(city, from_ms=None, to_ms=None, last_sec=None, detailed=False):
    """Index points: [{'t': event minute (unix ms), 'v': value F, 'status': 'normal'|'degraded'|'incomplete', 'contributors': n, 'stations': [...]}]."""
    p = {}
    if last_sec:
        p["last_sec"] = int(last_sec)
    else:
        if from_ms is not None:
            p["from"] = int(from_ms)
        if to_ms is not None:
            p["to"] = int(to_ms)
    if detailed:
        p["detailed"] = "true"
    return _get(f"/live_data/weather/{city}", p).get("timeseries", [])


def calibrations(city):
    """Configuration history: station weights and Celsius offsets, weekly re-estimates."""
    return _get(f"/live_data/weather/{city}/calibrations").get("calibrations", [])


def tick_f(n_stations):
    """Lattice step of the index in degrees F (whole-degree-C stations, equal weights)."""
    return 1.8 / n_stations


def cushion_ticks(index_value, strike, n_stations):
    """How many lattice steps the index sits above (+) or below (-) a 'greater than strike' threshold."""
    return (index_value - strike) / tick_f(n_stations)


def settlement_value(points, close_ms, max_age_min=60):
    """Value used for an 'at' contract closing at close_ms: canonical point with the greatest event time <= close, at most 60 min old."""
    ok = [p for p in points if p.get("v") is not None and p["status"] in ("normal", "degraded")
          and p["t"] <= close_ms and close_ms - p["t"] <= max_age_min * 60000]
    return max(ok, key=lambda p: p["t"])["v"] if ok else None


def outcome(points, close_ms, strike):
    """'yes' if the settlement value is strictly above the strike (markets use X.99 strikes), 'no' otherwise, None if undeterminable."""
    v = settlement_value(points, close_ms)
    return None if v is None else ("yes" if v > strike else "no")


def receipt_delays(points):
    """Seconds between each event minute and the receipt of each station reading (needs detailed=True): shows the ~135-150 s data latency."""
    out = []
    for p in points:
        for s in p.get("stations") or []:
            if s.get("received_at_ms") is not None:
                out.append((p["t"], s["station_id"], (s["received_at_ms"] - p["t"]) / 1000.0))
    return out
