# The budget axis is gated by score resolution, and a wider scale only sometimes fixes it

Reproduce with:

```
uv run python scripts/analysis_score_resolution.py
```

No API cost.

## The constraint

Every audit budget in this study is a percentile of the honest suspicion
distribution, and the library thresholds with strict `>`. So the achievable
false-positive rates are not the ones we ask for. They are exactly the set
`{mean(honest > v)}` over the distinct honest scores `v`. Ask for 0.5% on a
scale that cannot express it and you silently get the nearest rung it can.

The library's default prompt asks for an integer 0-10, and monitors use far
fewer values than that in practice. **The number of distinct scores a monitor
emits is the number of audit budgets it can be measured at.** This is the whole
reason a budget-indexed comparison is harder than a single-operating-point one,
and it is invisible to any threshold-free metric.

A rung also has to be *usable*. One honest row out of 500 is a 0.20% FPR whose
95% CI runs past 1%, so a safety number built on it rests on a single sample.
The criterion used below is at least 5 honest rows above the threshold.

## Measurement

n=500 honest + 500 attack, comments stripped, same dataset:

| monitor and scale | distinct, honest rows | distinct, all rows | usable rungs | lowest usable FPR | AUC |
|---|---|---|---|---|---|
| Haiku 5.5 xhigh, 0-10 (default) | 7 | 10 | 2 | 1.60% | 0.9422 |
| Haiku 5.5 xhigh, **0-100** | **14** | 77 | **8** | **1.00%** | 0.9481 |
| Haiku 5.5 xhigh, 0-200 | 14 | 103 | 8 | 1.00% | 0.9534 |
| Sonnet 5.5 UM, 0-10 (default) | 6 | 11 | 2 | 1.00% | 0.9577 |
| Sonnet 5.5 UM, **0-100** | 7 | 34 | 3 | 1.20% | 0.9593 |

> **Corrected 2026-11-01.** This table had a single "distinct scores" column
> carrying 10, 77, 103, 11 and 34, which are the distinct values over **all**
> 1,000 rows. That is the wrong quantity for the argument being made. An audit
> threshold is a percentile of the **honest** distribution, so the number of
> audit budgets a monitor can be measured at is set by its distinct **honest**
> scores, which are 7, 14, 14, 6 and 7. The two counts differ by up to 7x and
> they tell different stories: on honest rows the 0-200 scale buys nothing over
> 0-100, 14 against 14, where the all-rows count suggested it emitted a third
> more granularity. The usable-rung, floor and AUC columns were always computed
> correctly from the honest distribution and are unchanged.

## What this says

**Prompting for 0-100 quadruples Haiku's usable operating points, 2 to 8, and
lowers its floor from 1.60% to 1.00% FPR.** On the default scale, a
budget-indexed frontier for this monitor is two points. That is not a frontier.

**0-200 buys nothing.** It emits 103 distinct values against 0-100's 77, yet
yields the same 8 usable rungs and the same 1.00% floor. Past a point the
binding constraint stops being the scale and becomes the number of honest
samples, and more scale cannot buy what more samples must.

**The fix is monitor-dependent, not universal.** Sonnet goes from 2 usable rungs
to 3, and its lowest usable FPR gets slightly *worse* (1.00% to 1.20%). Sonnet
concentrates its honest scores tightly no matter how much room it is given, so
widening the scale does not spread them out. Any claim of the form "prompt for a
wider scale to get resolution" has to be made per monitor.

**AUC moves by at most 1.1 points across every row above.** Discrimination was
never the problem, and an AUC-only evaluation would show nothing wrong while the
budget axis was unmeasurable underneath it. This is the concrete case for
reporting the frontier rather than a summary statistic.

## Consequence for the study

The comparison rung has to be one both monitors can actually express with enough
honest rows behind it. Reporting a monitor at a budget its scale cannot reach
means reporting it at a different budget than the label claims.
