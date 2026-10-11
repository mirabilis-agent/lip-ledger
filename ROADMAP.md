# Roadmap

- [x] v0.1: exact side-scoring model, public-API client, CLI (`programs`, `score`), unit tests, rain-market dataset, post-mortem.
- [x] v0.2: snapshot recorder (public order books every minute) and analyzer to replace the "both sides counted 100% of the time" assumption with measured counted fractions.
- [ ] v0.3: per-series sweep statistics from public trade tapes (clip sizes, burst quantiles) and a "fill cost per resting hour" column next to each program's reward rate.
- [x] v0.3: static live table on the explainer page (docs/live.json), refreshed hourly by a GitHub Action.

Read-only by design: no order placement code will be added to this package.
