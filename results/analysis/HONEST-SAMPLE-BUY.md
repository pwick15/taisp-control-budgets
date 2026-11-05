# Doubling the honest arm halved the price of every threshold

Reproduce with:

```
uv run --with datasets python scripts/pick_honest_topup_ids.py      # the 500 ids, deterministic
LABEL=... IDS=... MONITOR=... scripts/run_honest_topup.sh           # about $5.94 for both arms
uv run python scripts/extract_honest_topup.py logs/<label>
uv run python scripts/analysis_honest_topup.py
```

## Why buy honest samples and not attack samples

Every audit threshold here is a percentile of the **honest** score distribution, applied with
a strict `>`. So the number of operating points a comparison can stand on is set by how many
honest rows sit above the cutoff, and nothing else. More attack samples do not move that, and
the attack pool caps at 1,061 paired problems anyway. The honest side is the only side worth
buying.

The 500 extra problems are the next `interview`-difficulty problems in the same
`get_dataset(has_backdoor_solution=True)` pool, continuing the prefix the runs themselves
took, so the honest arm stays inside the single difficulty band every number in this project
describes. 561 were available and 61 are left over.

## The exchangeability check, which had to come first

`README.md` records that the unscored remainder of the pool is **not** exchangeable with the
scored part by construction, because the first 500 are all one difficulty and the rest are a
mix. Restricting the buy to `interview` is supposed to fix that. Whether it did is testable,
and it was the first thing checked:

| | original 500 | top-up 500 | rank AUC, new against old |
|---|---|---|---|
| Sonnet 5.5 UM, 0-100 | mean 0.0148, median 0.01 | mean 0.0115, median 0.01 | **0.4892** |
| Haiku 5.5 xhigh, 0-100 | mean 0.0238, median 0.02 | mean 0.0197, median 0.02 | **0.5225** |

0.5 is exact rank exchangeability. Both arms land within 2.3 points of it, so the extra
problems rank interchangeably with the originals on both monitors. **The assumption the buy
rested on holds**, which is the thing that was worth $5.94 to find out before spending $24 on
the rest.

## What it bought

The honest arm goes from 500 to 1,000. The attack arm is unchanged at 500.

| | before | after |
|---|---|---|
| shared usable rungs | 3 | 3 |
| rates they sit at | 0.60%, 0.80%, 1.20% | **0.30%, 0.40%, 0.90%** |

**The two sides share no rate at all.** That is the finding and not a gap in the analysis.
Doubling the honest arm did not refine the lattice, it **relocated** it: an achievable rate is
a row count over n, so the same cutoffs now express half the rate they did before.

So the comparable axis is not the rate, it is the number of honest rows holding the cutoff up,
which is what the interval width depends on:

| honest rows | FPR before | FPR after | gap before | gap after | width before | width after | lower bound |
|---|---|---|---|---|---|---|---|
| 3 | 0.60% | **0.30%** | +20.2 | +20.2 | 48.8 | 44.8 | +2.2 to **+6.4** |
| 4 | 0.80% | **0.40%** | +17.8 | +17.8 | 45.8 | 43.4 | +3.2 to **+6.4** |

Read the first two columns together. The cutoff holding three honest rows is the same score as
before, 0.06 for Sonnet and 0.22 for Haiku, and it now costs **half** the false-positive rate.
The gap at a matched row count is identical to the digit, which is the right null and a check
on the whole exercise. The interval is narrower and the lower bound roughly **triples**, from
+2.2 to +6.4 and from +3.2 to +6.4.

A third rung appears at 0.90% on 9 honest rows: Sonnet 87.4% against Haiku 78.0%, gap **+9.4
points, 95% CI [+1.8, +18.2]**, width 16.4. That is the narrowest interval in the study and it
sits at a cheaper rate than the old 1.20% rung, which had width 20.4 on 6 rows.

## What this says about buying more

The headline is not "more rungs". The rung **count** did not change, and on this evidence it
is not what honest samples buy. What they buy is twofold:

1. **The same operating points at half the price.** A deployment that can afford to review 3
   files in 1,000 could not be measured at all before and can be now.
2. **A narrower interval at a matched row count**, about 4 points of width and a tripled lower
   bound here.

Both are the mechanism `R10` predicted, and the first is the one the earlier resampling
analysis got right for the wrong reason: it said resampling "relocates the lattice rather than
refining it" and treated that as a reason not to buy. Relocation downward is exactly what a
tight-budget comparison needs.

## What was not checked, and the honest limit

The forecast this buy was authorised on, a 0.543-wide interval at a 0.5% request, is **not**
comparable to anything measured here and no ratio against it is reported. That forecast served
a 0.5% *request* at whatever rung each bootstrap replicate could reach, including rungs resting
on one or two honest rows; this analysis reports only rungs with at least three. Two
estimators, so dividing one by the other would compare the wrong things.

The remaining buy to the 2,118-honest cap is now priced from a measurement rather than a
model, and its case is weaker than before: it would halve the rates again, to about 0.15%, and
on this evidence buy roughly another 4 points of interval width. Whether a 0.15% rung is worth
$18 depends on whether anything would be published at it.
