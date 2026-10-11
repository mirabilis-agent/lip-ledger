"""Command line: python -m lip_ledger programs [--prefix KXRAIN] [--qty 5] [--top 20] | score TICKER SIDE PRICE QTY"""
from __future__ import annotations
import argparse
import datetime as dt

from . import api, dashboard, recorder
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
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
