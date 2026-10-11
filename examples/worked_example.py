from lip_ledger import expected_payout, side_score

others = [(0.28, 120), (0.27, 300), (0.26, 450), (0.25, 600)]      # other participants' bids on one side
r = side_score(others, target=1000, d=0.5, mine=(0.28, 5))
print(r)
print("expected payout, $100 program, counted all the time, resting the whole program: $%.2f" % expected_payout(100, r["share"]))
