"""Snapshot recorder + analysis: measure how often a program's two sides are both 'counted' and what a hypothetical order would have scored.

LIP scores one-second snapshots; the public API only exposes the current order book, so a faithful estimate needs your own samples.
`record` stores one book per program per interval as JSON lines; `analyze` replays the file through the exact model.
"""
from __future__ import annotations
import datetime as dt
import json
import time

from . import api
from .model import expected_payout, side_score


def record(prefix, out_path, interval_s=60, minutes=60):
    """Append snapshots of every active program whose ticker starts with `prefix` to a JSONL file."""
    end = time.time() + minutes * 60
    progs = {p["market_ticker"]: p for p in api.active_programs() if p["market_ticker"].startswith(prefix)}
    with open(out_path, "a") as f:
        while time.time() < end and progs:
            books = api.orderbooks(progs.keys())
            now = dt.datetime.now(dt.timezone.utc).isoformat()
            for t, b in books.items():
                p = progs[t]
                f.write(json.dumps({"ts": now, "ticker": t, "target": float(p["target_size_fp"]), "d": (p.get("discount_factor_bps") or 5000) / 10000.0,
                                    "pool": p["period_reward"] / 10000.0, "yes": b["yes"], "no": b["no"]}, separators=(",", ":")) + "\n")
            f.flush()
            time.sleep(interval_s)


def analyze(path, qty, side="yes", at="best"):
    """Replay a snapshot file: per ticker, the share of snapshots where both sides were counted and the mean share of a hypothetical order
    (`qty` contracts at the best bid of `side`). Returns {ticker: dict}."""
    acc = {}
    for line in open(path):
        r = json.loads(line)
        both = all(side_score(r[s], r["target"], r["d"])["counted"] for s in ("yes", "no"))
        lv = r[side]
        a = acc.setdefault(r["ticker"], {"n": 0, "counted": 0, "share_sum": 0.0, "pool": r["pool"]})
        a["n"] += 1
        if both and lv:
            best = max(p for p, _ in lv)
            a["counted"] += 1
            a["share_sum"] += side_score(lv, r["target"], r["d"], mine=(best, qty))["share"]
    out = {}
    for t, a in acc.items():
        frac = a["counted"] / a["n"] if a["n"] else 0.0
        mean_share = a["share_sum"] / a["n"] if a["n"] else 0.0       # uncounted snapshots contribute 0
        out[t] = {"snapshots": a["n"], "counted_fraction": frac, "mean_share": mean_share,
                  "payout_if_resting_whole_program": expected_payout(a["pool"], mean_share)}
    return out
