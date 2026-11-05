# The deferral axis is the audit axis again, and coarser

Reproduce with:

```
uv run python scripts/analysis_defer_resolution.py
```

No API cost.

## Why look

The study's central methodological finding is that a requested audit budget is
not an achievable one. Thresholds are percentiles of a handful of distinct
honest scores, applied with strict `>`, so asking for 0.5% silently returns
whatever rung the scale can express.

Defer-to-trusted adds a second threshold of exactly the same construction, over
exactly the same honest scores: samples above the defer cutoff are replaced by
the trusted model's answer. If the diagnosis is right, the defer axis must
collapse the same way, and a defer sweep must realise fewer settings than it
requests. That is a falsifiable prediction about a protocol the project had not
examined, and it is answerable for nothing from a file already committed.

## What the sweep actually bought

`results/sonnet55-n100-haiku45-strip-dtt.csv`, Sonnet 5.5 writing and Haiku 4.5
monitoring and deferring, n=100 honest + 100 attack, 6 audit budgets x 8 defer
settings = 48 rows:

| | requested | realised |
|---|---|---|
| defer settings | 8 | **4** |
| distinct defer thresholds | 8 | **4** (`-inf`, `0.0`, `0.1`, `inf`) |
| deferral fractions | 0, 2, 5, 10, 20, 30, 50, 100% | **0%, 19%, 81%, 100%** |

Per audit budget, the 8 requested settings collapse to **3 distinct (deferral,
safety, usefulness) points**, and to 2 at a 20% budget.

Two of the four thresholds are infinite, which is to say they are not thresholds:
`-inf` defers everything and `inf` defers nothing.

**Read per audit budget it is worse than the pooled count suggests.** The pooled
set has two interior values, 19% and 81%, but no single audit budget offers both.
At every budget from 0.5% to 10%:

| asked to defer | actually deferred |
|---|---|
| 0%, 2%, 5%, 10% | **0%** |
| 20%, 30%, 50% | 19% |
| 100% | 100% |

So **asking to defer 10% of honest traffic defers nothing at all**, and three of
the eight requests are indistinguishable from asking for no deferral. Exactly
**one interior operating point** exists at any budget, and which one it is
depends on the budget rather than on the request: 19% below a 20% audit budget,
and 81% at 20%, where requests from 0% through 50% all defer nothing because
everything suspicious enough to defer has already been audited and only a 100%
request moves at all.

> **Corrected 2026-11-01**, same day. This section first said the sweep "has
> exactly two interior operating points", counting 19% and 81% from the pooled
> set. That pooled count is not available to an operator, who picks one audit
> budget and then has one interior setting, or none at 20%. The underlying point
> is unchanged and the corrected version is stronger.

## The usefulness axis is worse

Untrusted alone solves 95 of 100; trusted alone solves 70. So the whole
usefulness range the protocol can trade against safety is **25 points**, and the
sweep samples it at four values: 0.70, 0.79, 0.86, 0.95. The outer two are the
endpoints, which are definitions rather than measurements: deferral at 0% is
plain trusted monitoring and at 100% is the trusted model alone.

**One interior point at any usable budget, on a 25-point range.** A
safety-usefulness tradeoff curve drawn through that would be reporting an
interpolation between two endpoints as though it were data.

## What this changes

It removes a work item rather than adding one. A defer-to-trusted sweep was
proposed as a way to add a second axis to the comparison, estimated at $12. The
axis does not exist at this resolution, so the money would have bought a denser
request grid returning the same four answers. The first thing a defer study
needs is not more settings, it is a monitor whose honest scores are spread
across the range the deferral threshold has to move through, which is the same
score-resolution problem, met a second time, in a place nothing had looked.

There is a second, independent reason the usefulness axis is weak here, recorded
in `README.md`: in the n=500 runs honest `main_task_success` is `C` on 500 of
500, because the dataset ships reference solutions rather than generating them.
So untrusted-alone usefulness is identically 1.000 there and the tradeoff is an
analytic line through a constant. The n=100 run above is the only one where U
and T actually differ, which is why it is the one measured, and it is also the
one whose logs were not retained.

## The retention gap

`src/defer_sim.py` replays deferral offline for any (audit, defer) pair at zero
API cost, which is what made extending this look cheap. It cannot be re-run: it
needs the monitored eval logs and this configuration's were not kept, so the
committed CSV is the whole record. Extending the sweep means re-running the
monitor on those 100 problems first, about $5, and the conclusion above says not
to bother. Recorded because it is the same log-retention gap that leaves five
n=500 runs with no recoverable cost.
