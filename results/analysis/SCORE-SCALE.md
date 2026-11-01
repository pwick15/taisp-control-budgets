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

n=500 honest + 500 attack, comments stripped, same dataset. Every monitor that
has both a 0-10 and a wider-scale arm, nine pairs:

| monitor and scale | distinct, honest rows | distinct, all rows | usable rungs | lowest usable FPR | AUC |
|---|---|---|---|---|---|
| Haiku 5.5 xhigh, 0-10 (default) | 7 | 10 | 2 | 1.60% | 0.9422 |
| Haiku 5.5 xhigh, **0-100** | **14** | 77 | **8** | **1.00%** | 0.9481 |
| Haiku 5.5 xhigh, 0-200 | 14 | 103 | 8 | 1.00% | 0.9534 |
| Sonnet 5.5 UM, 0-10 (default) | 6 | 11 | 2 | 1.00% | 0.9577 |
| Sonnet 5.5 UM, **0-100** | 7 | 34 | 3 | 1.20% | 0.9593 |
| Gemma 3 4B, 0-10 (default) | 11 | 11 | 9 | 2.40% | 0.6171 |
| Gemma 3 4B, **0-100** | **29** | 34 | **23** | 2.60% | 0.6078 |
| Gemma 3 27B, 0-10 (default) | 9 | 10 | 6 | 1.20% | 0.7151 |
| Gemma 3 27B, **0-100** | **24** | 33 | **18** | 1.20% | 0.7263 |
| GPT-6 Luna, 0-10 (default) | 5 | 10 | 1 | 1.20% | 0.7683 |
| GPT-6 Luna, **0-100** | **10** | 69 | **4** | **1.00%** | **0.9107** |
| Gemma 4 26B-A4B, 0-10 (default) | 5 | 11 | **0** | **none** | 0.6490 |
| Gemma 4 26B-A4B, **0-100** | **7** | 29 | **2** | **1.00%** | **0.7336** |
| gpt-oss-120b, 0-10 (default) | 6 | 11 | 3 | 4.60% | 0.7593 |
| gpt-oss-120b, 0-100 (confounded) | 12 | 31 | 6 | 1.80% | 0.8316 |
| Qwen3.8 Omni Flash, 0-10 (default) | 5 | 11 | 1 | 1.80% | 0.7477 |
| Qwen3.8 Omni Flash, 0-100 (confounded) | 13 | 64 | 7 | 1.20% | 0.8969 |

**Two pairs are marked confounded and are excluded from every count below.**
Their 0-100 arms were launched without a `reasoning_effort` so the provider's
default applied, while their 0-10 counterparts carried an explicit setting. That
moves reasoning from 283 tokens per sample to none on gpt-oss-120b, and from
none to 1,281 on Qwen. Whatever those two rows show, the prompt is not the only
thing that changed, so nothing is attributed to it.

> **Corrected 2026-11-01.** When this table held only the first five rows above,
> it had a single "distinct scores" column carrying 10, 77, 103, 11 and 34, which
> are the distinct values over **all** 1,000 rows. That is the wrong quantity for
> the argument being made. An audit threshold is a percentile of the **honest**
> distribution, so the number of audit budgets a monitor can be measured at is
> set by its distinct **honest** scores, which for those five rows are 7, 14, 14,
> 6 and 7. The two counts differ by up to 7x and they tell different stories: on
> honest rows the 0-200 scale buys nothing over 0-100, 14 against 14, where the
> all-rows count suggested it emitted a third more granularity. Both columns are
> now shown. The usable-rung, floor and AUC columns were always computed
> correctly from the honest distribution and are unchanged.
>
> **Extended the same day** from two monitors to nine pairs, once the 0-100 arms
> existed for the rest of the cheap monitors. That is what turned "the fix is
> monitor-dependent" from a two-point observation into a measured count, and it
> is what surfaced the AUC move on GPT-6 Luna, which neither of the original two
> monitors shows.

## What this says

**The lever is general. Usable rungs rose on 7 of the 7 clean pairs**, from as
little as 2 to 3 (Sonnet) to as much as 9 to 23 (Gemma 3 4B). The first version
of this document measured two monitors and could not rule out that the effect
belonged to those two. It does not.

**Prompting for 0-100 quadruples Haiku's usable operating points, 2 to 8, and
lowers its floor from 1.60% to 1.00% FPR.** On the default scale, a
budget-indexed frontier for this monitor is two points. That is not a frontier.

**More rungs is not the same as a cheaper rung, and the difference decides
whether this buys anything. The cheapest usable rate fell on only 4 of the 7.**
Sonnet goes 1.00% to 1.20% and Gemma 3 4B 2.40% to 2.60%, both slightly *worse*,
while gaining rungs higher up. A monitor that concentrates its honest scores
keeps concentrating them wherever the scale ends; the extra values land above
the mode, where budget is cheap and nobody needs more resolution.

**The one unambiguous win is Gemma 4 26B-A4B, which had no usable rung at all.**
On 0-10 its five distinct honest scores put every achievable rate either at zero
or above the 5-row bar's reach, so the monitor could not be placed on a budget
axis in any form. On 0-100 it has two rungs and a 1.00% floor. That is the
difference between a monitor that can be compared and one that cannot.

**0-200 buys nothing.** It emits 103 distinct values against 0-100's 77, yet
yields the same 8 usable rungs and the same 1.00% floor. Past a point the
binding constraint stops being the scale and becomes the number of honest
samples, and more scale cannot buy what more samples must.

**On two monitors the wider prompt is not a resolution change at all, it is a
better detector.** AUC moves by at most 1.1 points on five of the seven clean
pairs, which is the behaviour this document originally reported and the reason
resolution and discrimination were treated as separate axes. GPT-6 Luna breaks
it: **0.7683 to 0.9107, +14.2 points**, on the same model, the same route, the
same stripping and within 4% on reasoning tokens. Gemma 4 26B-A4B moves +8.5.
Asking those two for a finer number makes them meaningfully better at the task,
not merely more granular about it.

That has a direct consequence: **for those two monitors the 0-10 and 0-100 arms
cannot be pooled into one frontier**, because they are not the same detector
measured at more points. The wider arm is the one to report, and the pair is
evidence about prompt sensitivity rather than two readings of one monitor.

**Discrimination was still never the problem for the monitors the study leads
with.** Haiku moves +0.6 and Sonnet +0.2, so an AUC-only evaluation of the
headline pair would have shown nothing wrong while the budget axis was
unmeasurable underneath it. This remains the concrete case for reporting the
frontier rather than a summary statistic; it is now also a case for reporting
both, since on Luna the summary statistic is where the whole effect is.

## Consequence for the study

The comparison rung has to be one both monitors can actually express with enough
honest rows behind it. Reporting a monitor at a budget its scale cannot reach
means reporting it at a different budget than the label claims.
