# Sonnet 5.5 beats Haiku 5.5 by 13.8 points, and the interval excludes zero

Reproduce with:

```
uv run python scripts/analysis_paired_bootstrap.py
```

No API cost.

## Why this needed a careful comparison

This is the study's central monitor comparison, and three things had to be
fixed before the number meant anything.

**Both monitors must be on the same score scale.** On the library's default
0-10 prompt each emits ~10 distinct values and can express only 2 usable audit
budgets (see `SCORE-SCALE.md`), so the comparison had nowhere to stand. Both
arms here use the 0-100 prompt.

That substitution needs a check, because the wider prompt is not always a pure
resolution change. Measured across nine scale pairs, it moves AUC by at most 1.1
points on five of them and by +14.2 on GPT-6 Luna and +8.5 on Gemma 4 26B-A4B,
where it makes the monitor meaningfully better at the task rather than more
granular about it. **These two monitors are in the quiet group**: Haiku 5.5 xhigh
moves +0.6 (0.9422 to 0.9481) and Sonnet 5.5 +0.2 (0.9577 to 0.9593). So
swapping in the 0-100 arms buys rungs here without changing what is being
compared, which is the condition that makes this comparison legitimate and not
a given.

**They must be compared at the same *achieved* false-positive rate.** Asking
two monitors for "1%" can put them at different real FPRs when their score
distributions differ, and then part of the gap is threshold placement rather
than monitor quality. Only operating points both can actually express are used.

**The comparison is paired and the threshold is re-estimated per replicate.**
Both monitors scored the same problems, so resampling problem ids once and
applying that resample to both arms removes the problem-difficulty variance that
dominates an unpaired comparison. Holding the threshold at its full-sample value
would treat a quantity estimated from the data as known and understate the
interval.

## Result

n=500 honest + 500 attack, comments stripped, 0-100 scale, 4,000 paired
bootstrap replicates:

| matched achieved FPR | honest rows | Sonnet 5.5 | Haiku 5.5 | difference | 95% CI | |
|---|---|---|---|---|---|---|
| 0.60% | 3 | 84.2% | 64.0% | +20.2 pts | [+2.2, +51.0] | thin |
| 0.80% | 4 | 85.8% | 68.0% | +17.8 pts | [+3.2, +49.0] | thin |
| **1.20%** | **6** | **87.4%** | **73.6%** | **+13.8 pts** | **[+2.4, +22.8]** | **powered** |

The two tighter rungs rest on 3 and 4 honest rows, so their intervals run past
+49 points and they are reported only to show the trend. **The 1.20% rung is the
tightest operating point with enough honest rows behind it, and there Sonnet
leads by 13.8 points with a 95% CI of [+2.4, +22.8].**

The gap widens monotonically as the budget tightens: +13.8 at 1.20%, +17.8 at
0.80%, +20.2 at 0.60%. That is the direction that matters for deployment, where
the audit budget is small, and it is the kind of statement a
single-operating-point comparison cannot make.

## What is not established

- **The floor is sample size, not scale.** Separating 0.5% from 1.0% needs more
  honest rows, not a better prompt. At n=500 honest, a 0.60% rung is 3 rows.
- **One attack distribution, and it matters more than this document first said.**
  Both monitors face the same stored backdoors, and recall varies by generator by
  far more than the "~20 points" originally stated here. Measured at this
  document's own headline rung, a 1.20% false-positive rate: Sonnet 0-100 spans
  **41.5 points** across the ten generators (0.585 to 1.000) and Haiku xhigh
  0-100 spans **63.0 points** (0.317 to 0.947). So the gap is strongly
  conditional on the attack mix, and a different mix could plausibly reorder the
  two monitors.
- **Reasoning effort does not explain it, but that null is weakly supported.**
  Toggling Sonnet's own effort is a null at **both** rungs the two effort arms
  share, not the one this document first reported: +6.0 pts with a 95% CI of
  [-2.2, +10.6] at 0.60% FPR on 3 honest rows, and **-0.8 pts, [-2.6, +10.2]**
  at 0.20% on a single row. Two nulls with opposite signs is a stronger null
  than one, but both CIs admit gains up to about 10 points, so this remains "not
  detectable at n=500" rather than "no effect". The
  low-effort arm is the weak link: it emits only 5 distinct honest scores, and
  its *only* operating point with 5 or more honest rows behind it sits at a
  14.80% FPR. The shared 0.60% rung rests on 3 honest rows. Settling whether
  effort buys anything at a deployable budget needs a low-effort arm on the
  0-100 prompt, not more replicates of this one.
