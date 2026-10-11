"""Build a JSON snapshot of the best modelled resting orders across all active LIP programs (public data only)."""
from __future__ import annotations
import datetime as dt
import json

from . import api
from .model import expected_payout, side_score


def _parse(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def build(qty=5.0, top=60, prefix=""):
    now = dt.datetime.now(dt.timezone.utc)
    progs = [p for p in api.active_programs() if p["market_ticker"].startswith(prefix)]
    books = api.orderbooks({p["market_ticker"] for p in progs})
    rows, counted_programs = [], 0
    for p in progs:
        b = books.get(p["market_ticker"])
        if not b:
            continue
        target = float(p["target_size_fp"])
        d = (p.get("discount_factor_bps") or 5000) / 10000.0
        if not all(side_score(b[s], target, d)["counted"] for s in ("yes", "no")):
            continue
        counted_programs += 1
        pool = p["period_reward"] / 10000.0
        total_h = max((_parse(p["end_date"]) - _parse(p["start_date"])).total_seconds() / 3600.0, 1e-9)
        left_h = max((_parse(p["end_date"]) - now).total_seconds() / 3600.0, 0.0)
        for side in ("yes", "no"):
            lv = b[side]
            best = max(pr for pr, _ in lv)
            r = side_score(lv, target, d, mine=(best, qty))
            pay = expected_payout(pool, r["share"], 1.0, min(1.0, left_h / total_h))
            rows.append({"ticker": p["market_ticker"], "side": side, "price": round(best, 2), "share": round(r["share"], 5),
                         "payout": round(pay, 2), "collateral": round(qty * best, 2), "hours_left": round(left_h, 1),
                         "pool": round(pool, 2), "target": target, "cheap_leg": best <= 0.10})
    rows.sort(key=lambda r: -r["payout"])
    return {"generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "qty": qty, "programs_active": len(progs),
            "programs_counted_now": counted_programs, "rows": rows[:top],
            "note": "Modelled payout for resting `qty` contracts at the best bid for the rest of the program, assuming both sides stay counted. "
                    "Cheap legs (<= 10c) are flagged: fills there are usually informed. $1.00 minimum payout applies per program."}


def write(path, qty=5.0, top=60, prefix=""):
    data = build(qty, top, prefix)
    with open(path, "w") as f:
        json.dump(data, f, separators=(",", ":"))
    return data
