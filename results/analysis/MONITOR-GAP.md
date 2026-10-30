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
- **One attack distribution.** Both monitors face the same stored backdoors, and
  recall is known to vary by generator by ~20 points, so the gap is conditional
  on this attack mix.
- **Reasoning effort does not explain it.** Toggling Sonnet's own effort is a
  null at the single rung the two effort arms share: 0.60% FPR, +6.0 pts, 95% CI
  [-2.4, +10.6]. The CI admits gains up to ~10 points, so this is "not
  detectable at n=500", not "no effect".
