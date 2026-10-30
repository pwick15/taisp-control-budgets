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
- [ ] Price Gemini 3.5 Flash and Gemma in `src/analyze.py` so they get a cost.

## Higher cost

- [ ] Live red team against the top 3 monitors, with defer-to-trusted for a usefulness number.
- [ ] Repeat runs to measure run-to-run variance.
