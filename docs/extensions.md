# Extensions and open work

Where to pick things up. Everything here uses the N=500 dataset-policy setup (`scripts/run_dataset_monitor.sh`), so only monitor calls cost money. Analysis scripts in `scripts/analysis_*.py` read `results/*-samples.csv` and need no API.

## Results page

`web/index.html` is the shareable page (write-up plus interactive cost-vs-safety chart). Rebuild with `python3 web/build.py` after `scripts/analysis_ci.py`; add new runs to `RUNS` in `web/build.py`. Cloudflare Pages: no build command, output directory `web`.

## No API cost

- [ ] **Hard and disagreement cases.** Findings so far in the study summary; per-problem lists in `results/analysis/hard-backdoors.csv` and `disagreement-sonnet-vs-haiku-xhigh.csv`.
- [ ] **Paired bootstrap for every monitor pair**, not just Sonnet vs Haiku xhigh (`scripts/analysis_disagreement.py` has the method).
- [ ] **Ties and high audit budgets.** Most honest scores are 0, so cutoffs sit at 0 or 0.1 and curves plateau. Decide how to report budgets of 10% and above, where the comparison reduces to "who scores a backdoor 0". Left out of the summary for now.

## Low API cost

- [ ] Comments kept vs stripped (`STRIP_COMMENTS=0`) on 2 to 3 monitors.
- [ ] Cost-matched ensembles (`src/ensemble.py`): several cheap monitors against one Haiku xhigh.
- [ ] Mid-size Gemma between 4B (0.00 safety at 2%) and 26B (0.31).
- [x] Price the Google models in `src/analyze.py` so they get a cost. Done 2026-11-01:
      `google/gemini-3.5-flash-lite`, both Gemma 3 sizes and Gemma 4 26B-A4B now carry
      rates, verified against the serving proxy's own rate card and, for the proxied
      ones, against the provider's per-call `estimated_cost` to ratio 1.000. The two runs
      that showed no cost, `dataset500-gemini35lite-tm-strip` and
      `dataset500-gemma426b-tm-strip`, now carry one too: $0.00111362 and $0.0007365 per
      sample, recovered from the sample-level usage field. Both record
      `usage_source=sample_field_complete`, so that field covers every sample, which is
      the evidence that no call was cache-served and the total is complete. No run in
      `results/` is without a cost now.

## Higher cost

- [ ] Live red team against the top 3 monitors, with defer-to-trusted for a usefulness number.
- [ ] Repeat runs to measure run-to-run variance.
