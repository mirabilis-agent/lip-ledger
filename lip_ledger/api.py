"""Tiny read-only client for Kalshi's PUBLIC endpoints (no API key needed)."""
from __future__ import annotations
import json
import urllib.parse
import urllib.request

BASE = "https://api.elections.kalshi.com/trade-api/v2"


def _get(path, params=None, timeout=30):
    url = BASE + path + ("?" + urllib.parse.urlencode(params, doseq=True) if params else "")
    req = urllib.request.Request(url, headers={"User-Agent": "lip-ledger/0.1 (read-only research tool)"})
    return json.load(urllib.request.urlopen(req, timeout=timeout))


def active_programs():
    """All active liquidity programs with a target size (dicts straight from the API)."""
    out, cur = [], None
    while True:
        d = _get("/incentive_programs", {"status": "active", "type": "liquidity", "limit": 10000, **({"cursor": cur} if cur else {})})
        out += [p for p in d.get("incentive_programs", []) if p.get("target_size_fp")]
        cur = d.get("next_cursor")
        if not cur:
            return out


def orderbooks(tickers):
    """{ticker: {"yes": [(price, size)], "no": [(price, size)]}} (bids on each side), fetched 100 at a time."""
    books, tickers = {}, list(tickers)
    for i in range(0, len(tickers), 100):
        d = _get("/markets/orderbooks", {"tickers": tickers[i:i + 100]})
        for ob in d.get("orderbooks", []):
            o = ob["orderbook_fp"]
            books[ob["ticker"]] = {"yes": [(float(p), float(s)) for p, s in o.get("yes_dollars", [])],
                                   "no": [(float(p), float(s)) for p, s in o.get("no_dollars", [])]}
    return books
