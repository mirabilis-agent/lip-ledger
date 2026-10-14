"""Command line: python -m lip_ledger programs [--prefix KXRAIN] [--qty 5] [--top 20] | score TICKER SIDE PRICE QTY"""
from __future__ import annotations
import argparse
import datetime as dt

from . import api, dashboard, recorder, windex
from .model import expected_payout, side_score


def _parse(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _program_eval(p, book, qty):
    target = float(p["target_size_fp"])
    d = (p.get("discount_factor_bps") or 5000) / 10000.0
    pool = p["period_reward"] / 10000.0
    now = dt.datetime.now(dt.timezone.utc)
    total_h = max((_parse(p["end_date"]) - _parse(p["start_date"])).total_seconds() / 3600.0, 1e-9)
    left_h = max((_parse(p["end_date"]) - now).total_seconds() / 3600.0, 0.0)
    both = all(side_score(book[s], target, d)["counted"] for s in ("yes", "no"))
    rows = []
    for side in ("yes", "no"):
        lv = book[side]
        if not lv:
            continue
        best = max(pr for pr, _ in lv)
        r = side_score(lv, target, d, mine=(best, qty))
        pay = expected_payout(pool, r["share"], 1.0, min(1.0, left_h / total_h))
        rows.append({"ticker": p["market_ticker"], "side": side, "price": best, "share": r["share"], "payout": pay,
                     "counted_now": r["counted"] and both, "hours_left": left_h, "cost": qty * best})
    return rows


def cmd_programs(a):
    progs = [p for p in api.active_programs() if p["market_ticker"].startswith(a.prefix)]
    books = api.orderbooks({p["market_ticker"] for p in progs})
    rows = []
    for p in progs:
        if p["market_ticker"] in books:
            rows += _program_eval(p, books[p["market_ticker"]], a.qty)
    rows = [r for r in rows if r["counted_now"]]
    rows.sort(key=lambda r: -(r["payout"] / max(r["cost"], 1e-9)))
    print(f"{len(progs)} active programs; showing top {a.top} counted sides by modelled payout per $ of resting collateral (qty {a.qty} at the best bid)")
    print("ticker                          side price  share    payout  cost   payout/$  hrs_left  note")
    for r in rows[: a.top]:
        note = "CHEAP LEG: fills are usually informed; check the outcome is not decided" if r["price"] <= 0.10 else ""
        print(f"{r['ticker']:32s} {r['side']:4s} {r['price']:.2f} {r['share']:7.4f} ${r['payout']:6.2f} ${r['cost']:5.2f} {r['payout']/max(r['cost'],1e-9):8.2f} {r['hours_left']:8.1f}  {note}")
    print("\nModelled payout assumes both sides stay counted for the rest of the program; the $1.00 minimum payout applies per program.")


def cmd_score(a):
    progs = [p for p in api.active_programs() if p["market_ticker"] == a.ticker]
    if not progs:
        raise SystemExit("no active program with a target size for that ticker")
    p = progs[0]
    book = api.orderbooks([a.ticker])[a.ticker]
    target = float(p["target_size_fp"])
    d = (p.get("discount_factor_bps") or 5000) / 10000.0
    r = side_score(book[a.side], target, d, mine=(a.price, a.qty))
    pool = p["period_reward"] / 10000.0
    print(f"target {target:.0f}, d={d}, pool ${pool:.2f}; side counted={r['counted']} ref={r['ref']} share={r['share']:.5f}")
    print(f"expected payout if counted 100% of the time for the rest of the program: ${expected_payout(pool, r['share']):.2f} (before the $1.00 floor)")


def cmd_record(a):
    recorder.record(a.prefix, a.out, a.interval, a.minutes)


def cmd_analyze(a):
    res = recorder.analyze(a.file, a.qty, a.side)
    print("ticker                           snaps counted%  mean_share  payout_if_rested_whole_program")
    for t, r in sorted(res.items(), key=lambda kv: -kv[1]["payout_if_resting_whole_program"])[: a.top]:
        print(f"{t:32s} {r['snapshots']:5d} {100*r['counted_fraction']:7.1f} {r['mean_share']:11.5f}  ${r['payout_if_resting_whole_program']:.2f}")


def cmd_windex(a):
    pts = windex.index(a.city, last_sec=(a.minutes + 8) * 60, detailed=True)   # newest minutes are still 'incomplete' (readings pending QC)
    pts.sort(key=lambda p: p["t"])
    n = max((len(p.get("stations") or []) for p in pts), default=0)
    print(f"{a.city}: {len(pts)} points, {n} stations, lattice step {windex.tick_f(max(n, 1)):.3f} F")
    for p in pts[-a.minutes:]:
        t = dt.datetime.fromtimestamp(p["t"] / 1000, dt.timezone.utc).strftime("%H:%M")
        st = " ".join(f"{s['station_id'][:4]}={s['temp_f']:.1f}" for s in p.get("stations") or [] if s.get("temp_f") is not None)
        d = [s["received_at_ms"] - p["t"] for s in p.get("stations") or [] if s.get("received_at_ms")]
        lat = f"{min(d)/1000:.0f}-{max(d)/1000:.0f}s" if d else "-"
        v = f"{p['v']:.2f}" if p.get("v") is not None else "pending"
        print(f"{t} {p['status']:10s} index {v:>8s}  received {lat:>8s}  {st}")


def cmd_windex_strikes(a):
    city = windex.SERIES_CITY.get(a.series)
    if not city:
        raise SystemExit("series must be one of " + ", ".join(windex.SERIES_CITY))
    pts = windex.index(city, last_sec=1200, detailed=True)
    pts = [p for p in pts if p.get("v") is not None]
    if not pts:
        raise SystemExit("no canonical index points yet")
    last = max(pts, key=lambda p: p["t"])
    n = max(len(p.get("stations") or []) for p in pts) or 5
    mk = api._get("/markets", {"series_ticker": a.series, "status": "open", "limit": 40}).get("markets", [])
    print(f"{city}: latest canonical index {last['v']:.2f} F (event minute {dt.datetime.fromtimestamp(last['t']/1000, dt.timezone.utc):%H:%M}Z), lattice {windex.tick_f(n):.3f} F")
    print("strike    bid   ask  cushion(ticks)  closes")
    for m in sorted(mk, key=lambda m: (m["close_time"], float(m.get("floor_strike") or 0))):
        k = float(m.get("floor_strike") or 0)
        print(f"{k:7.2f}  {float(m.get('yes_bid_dollars') or 0):.2f}  {float(m.get('yes_ask_dollars') or 0):.2f}  {windex.cushion_ticks(last['v'], k, n):+9.1f}      {m['close_time'][11:16]}Z")


def cmd_windex_json(a):
    """Snapshot for the dashboard: per active hourly-index series the latest canonical index, station readings, lattice step, receipt latency, open strikes."""
    import json
    out = {"generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "cities": []}
    for series, city in windex.SERIES_CITY.items():
        try:
            pts = [p for p in windex.index(city, last_sec=1200, detailed=True) if p.get("v") is not None]
            last = max(pts, key=lambda p: p["t"])
            st = [s for s in last.get("stations") or [] if s.get("temp_f") is not None]
            n = max(len(st), 1)
            mk = api._get("/markets", {"series_ticker": series, "status": "open", "limit": 40}).get("markets", [])
            strikes = []
            for m in sorted(mk, key=lambda m: (m["close_time"], float(m.get("floor_strike") or 0))):
                k = float(m.get("floor_strike") or 0)
                strikes.append({"strike": k, "bid": float(m.get("yes_bid_dollars") or 0), "ask": float(m.get("yes_ask_dollars") or 0),
                                "closes": m["close_time"], "cushion_ticks": round(windex.cushion_ticks(last["v"], k, n), 1)})
            lat = [(s["received_at_ms"] - last["t"]) / 1000.0 for s in st if s.get("received_at_ms")]
            out["cities"].append({"city": city, "series": series, "index": last["v"], "event_minute": last["t"], "tick_f": round(windex.tick_f(n), 3),
                                  "stations": {s["station_id"]: s["temp_f"] for s in st}, "receipt_latency_s": [round(min(lat)), round(max(lat))] if lat else None,
                                  "strikes": strikes})
        except Exception as e:  # keep the snapshot usable if one city fails
            out["cities"].append({"city": city, "series": series, "error": str(e)[:100]})
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"wrote {a.out}: {len(out['cities'])} cities")


def cmd_dashboard(a):
    d = dashboard.write(a.out, a.qty, a.top, a.prefix)
    print(f"wrote {a.out}: {len(d['rows'])} rows, {d['programs_counted_now']} of {d['programs_active']} programs counted now")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lip_ledger")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s1 = sub.add_parser("programs"); s1.add_argument("--prefix", default=""); s1.add_argument("--qty", type=float, default=5.0); s1.add_argument("--top", type=int, default=20)
    s1.set_defaults(fn=cmd_programs)
    s2 = sub.add_parser("score"); s2.add_argument("ticker"); s2.add_argument("side", choices=["yes", "no"]); s2.add_argument("price", type=float); s2.add_argument("qty", type=float)
    s2.set_defaults(fn=cmd_score)
    s3 = sub.add_parser("record"); s3.add_argument("--prefix", required=True); s3.add_argument("--out", default="books.jsonl")
    s3.add_argument("--interval", type=int, default=60); s3.add_argument("--minutes", type=int, default=60); s3.set_defaults(fn=cmd_record)
    s4 = sub.add_parser("analyze"); s4.add_argument("file"); s4.add_argument("--qty", type=float, default=5.0)
    s4.add_argument("--side", choices=["yes", "no"], default="yes"); s4.add_argument("--top", type=int, default=20); s4.set_defaults(fn=cmd_analyze)
    s5 = sub.add_parser("dashboard"); s5.add_argument("--out", default="live.json"); s5.add_argument("--qty", type=float, default=5.0)
    s5.add_argument("--top", type=int, default=60); s5.add_argument("--prefix", default=""); s5.set_defaults(fn=cmd_dashboard)
    s6 = sub.add_parser("windex"); s6.add_argument("city", help="nyc | chicago | la-coastal | miami | ..."); s6.add_argument("--minutes", type=int, default=15)
    s6.set_defaults(fn=cmd_windex)
    s7 = sub.add_parser("windex-strikes"); s7.add_argument("series", help="KXTEMPNYCHS | KXTEMPLAXHS | KXTEMPCHIHS | KXTEMPMIAH")
    s7.set_defaults(fn=cmd_windex_strikes)
    s8 = sub.add_parser("windex-json"); s8.add_argument("--out", default="windex.json"); s8.set_defaults(fn=cmd_windex_json)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
