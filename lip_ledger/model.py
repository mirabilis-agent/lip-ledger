"""Exact LIP side-scoring model (CFTC filing, clean terms effective 2026-07-30).

Per one-second snapshot each side of the book (yes bids / no bids) is scored separately:
  1. Walk price levels from the best bid down, accumulating WHOLE levels.
  2. Reference price = first level where cumulative size >= target / 5.
  3. Qualifying bids = levels up to and including the first level where cumulative size >= target.
     If a side never reaches the target nothing qualifies and the snapshot is excluded (both sides must reach it).
  4. score = size * d ** (ticks below the reference price, floored at 0), d = discount_factor_bps / 10000.
  5. Payout = pool * 0.5 * (your normalised share of a side) * (counted snapshots / all snapshots), per side you quote,
     paid in one daily batch after the program ends and only if the amount is >= $1.00.
"""
from __future__ import annotations


def side_score(levels, target, d, mine=None, tick=0.01):
    """levels: iterable of (price, size) of OTHER participants on one side; mine: optional (price, size) hypothetical order.

    Returns dict(counted, ref, total_score, my_score, share). `share` is 0.0 when the side is not counted."""
    agg: dict[float, list[float]] = {}
    for price, size in levels:
        agg.setdefault(round(float(price), 4), [0.0, 0.0])[0] += float(size)
    if mine:
        agg.setdefault(round(float(mine[0]), 4), [0.0, 0.0])[1] += float(mine[1])
    cum, ref, qualifying, reached = 0.0, None, [], False
    for price in sorted(agg, reverse=True):
        other, own = agg[price]
        cum += other + own
        qualifying.append((price, other, own))
        if ref is None and cum >= target / 5.0:
            ref = price
        if cum >= target:
            reached = True
            break
    if not reached:
        return {"counted": False, "ref": ref, "total_score": 0.0, "my_score": 0.0, "share": 0.0}
    total = mine_s = 0.0
    for price, other, own in qualifying:
        ticks = max(0, round((ref - price) / tick))
        w = d ** ticks
        total += w * (other + own)
        mine_s += w * own
    return {"counted": True, "ref": ref, "total_score": total, "my_score": mine_s, "share": (mine_s / total) if total else 0.0}


def expected_payout(pool_dollars, share, counted_fraction=1.0, present_fraction=1.0):
    """pool * 0.5 * share * counted_fraction * present_fraction (per side). Remember the $1.00 minimum payout."""
    return pool_dollars * 0.5 * share * counted_fraction * present_fraction
