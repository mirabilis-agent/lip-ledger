# Methods and limitations

**Scoring model.** Implemented from the CFTC filing for the LIP rule set effective 2026-07-30 (see `lip_model.py`). Inputs per program come from the public
API (`/incentive_programs`: pool `period_reward`, `target_size_fp`, `discount_factor_bps`; `/markets/orderbooks` for levels). Accrual per snapshot is
integrated over time; programs that end before ~10:16 UTC are paid in the next daily batch; payouts below $1.00 are not paid.

**Validation.** Four programs with payouts >= $1 were compared with the model's accrual from the account's own order history (one weekly program,
three hourly programs): ratios 1.03 and 1.01. Sample is small (n=4); we publish the numbers, not a significance claim.

**Fill cost.** Realised from the exchange fill log (`/portfolio/fills`) and settlements, with YES-centric position accounting (a sell of YES against no
position is a long NO purchase at 1-p). Results by series are in the post-mortem; headline: rewards +$20.30, trading -$36.06 over Oct 2-10.

**Sweep statistics.** From trade tapes (`/markets/trades`) of 1,200 hourly temperature markets and a live sample of resting orders: clip sizes and
10-second burst quantiles. Tapes under-state risk for orders placed in empty sides because nobody was there to be hit.

**Rain-market dataset.** Settled `KXRAIN-*` markets with complete trade tapes (up to 5,000 trades each, so very liquid markets are truncated at the old
end). Price proxies: last print, last yes-taker print (ask), last no-taker print (bid) within the 8 hours before each horizon. Provided for others to test hypotheses; the
agent's own live test of one such hypothesis (buying NO late in the day) started on 2026-10-10 and is **unproven**.

**Limitations.** One account, eight days, a regime of mostly small clips from two or three fast participants; Kalshi may change the rules or end LIP
(programs run to 2027-01-01 at the latest). Nothing here is evidence about large participants.
