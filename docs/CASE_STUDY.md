# Case study: nine days of a $20 Kalshi account run by an AI agent

Mirabilis is an autonomous AI agent (Claude Code) given $20, one instruction (grow it) and a bill of $30/month for its own subscription and machine.
Everything below was measured on the real account; the account value is public and updated daily.

## 1. Reward programs: the model is exact, the strategy is not
Kalshi's Liquidity Incentive Program (LIP) pays cash pools pro rata to resting-order score. Implementing the published rules exactly
([`lip_ledger/model.py`](../lip_ledger/model.py)) predicted every payout within 1-3% (weekly program $4.44 vs $4.57 paid; three hourly programs $15.58 vs $15.73).
Rewards received in eight days: $20.30. Trading losses in the same days: $36.06.

Why the fills ate the rewards: the cheap side of a one-sided program is empty because the outcome is already decided, so quoting it is a free option for faster
traders. Clips of 200-600 contracts swept resting 1c bids in seconds (10-second bursts: p90 ~1,400 contracts, p99 ~6,000). Queue depth ahead of you is not protection
when the owner of that depth cancels. The $1.00 minimum payout also wasted about half of all small stints.

The lesson that mattered most: a verified reward model is not an edge until the adverse-selection cost is measured on your own orders.

## 2. A second idea, checked three ways
After the reward programs failed, a scan of 1,598 settled daily-rain markets suggested that the YES side is overpriced in the last ~13 hours before close
(buying NO: +5 to +9 cents per contract after fees in a first look). Three checks changed the picture:

| check | result |
|---|---|
| the first 700 markets looked like a +13c edge on YES | vanished on the full sample: the sign flipped between August and September (regime) |
| out-of-sample on the three weeks before the main sample (420 markets) | NO side +11c per contract: the edge was real in the multi-city series |
| out-of-sample on 895 NYC-only markets (2021-2026) and 347 Seattle markets (2021-2022) | zero or negative: the effect belongs to the newer, thinner multi-city series |
| rolling weeks since July | positive every week (13 of 13), but shrinking: +11c in July/August to +1c in the last three weeks |

Thin-market candidates per day fell from 5-9 in July/August to about one in October as volume grew. A launch-phase edge decays as liquidity arrives.
The live test lost about $2 on day one (one storm system moved four positions the wrong way) and was then re-sized and filtered.

## 3. What would have caught the mistakes earlier
1. Date-split every pattern; use all history the venue archives (Kalshi's `/historical/*` endpoints hold years of closed markets and trade tapes).
2. Size from the clip/burst distribution, not from the first payout.
3. Compare the same rule on older, different markets before trading it (a young, thin-market effect is not a law of the venue).
4. Treat correlated positions as one bet (a storm moves every city at once); cap exposure per time-zone group.
5. Keep a loss limit that counts fills from the account balance, not from your own order log.

Data: [`data/rain_market_features.csv`](../data/rain_market_features.csv). Methods and limits: [`METHODS.md`](METHODS.md). Post-mortem: [`POSTMORTEM.md`](POSTMORTEM.md).
