# GLM-5.3: what the two existing runs are

## The provider default IS `max`

DeepInfra's integration guide states: "`reasoning_effort` ... Accepts low, high
or max. Defaults to max when omitted or set to any other value. Keep max to
reproduce published benchmark results."

Verified on the live endpoint. Temperature 0, same prompt, reasoning tokens:

| setting | reps | reasoning tokens |
|---|---|---|
| unset | 4 | 395, 298, 310, 392 |
| `max` | 4 | 387, 622, 375, 358 |
| `high` | 4 | 190, 193, 319, 196 |
| `low` | 4 | 167, 161, 198, 155 |

At temperature 1, n=12 each: unset median 358, `max` median 368. Indistinguishable,
while `high` and `low` are clearly lower.

**So `dataset-glm53-tm-n500-strip` is the `max` rung.** A low/high/max ladder
needs only `low` and `high` added.

(An earlier note here claimed the default was *not* max. That was wrong: it came
from n=6 at temperature 1, where one 3,251-token outlier dragged the mean. GLM's
reasoning length is highly variable per call, so small samples mislead.)

## `reasoning_effort="none"` is NOT a usable ablation, and NOT a duplicate

Z.ai documents that GLM-5.3 "uses forced thinking and cannot be disabled" and
accepts only `low`, `high`, `max`. DeepInfra says any other value falls back to
`max`. But `none` does not behave like `max`:

| setting | completion | reasoning reported | visible (completion - reasoning) |
|---|---|---|---|
| `none` | 553, 501 | **0** | ~553 |
| unset | 453, 454 | 325, 310 | ~128 |
| `max` | 552, 637 | 341, 363 | ~211 |

Over the 500-problem run, paired across the 999 samples both arms scored and
with usage recovered from the model events: `none` used **5,689 output tokens
per sample against max's 5,603, which is +1.5%**, and **6,875 total against
6,789, +1.3%**, while reporting **no reasoning tokens at all** against max's
5,101. It scored the same (0.760 vs 0.762) with an identically-sized parsed
`<reasoning>` block (~1,826 characters in both).

So the two arms generate the same volume and differ only in how it is labelled.
The harness stores only the parsed `MonitorResponse`, not the raw completion, so
the logs cannot say directly whether thinking was disabled or moved into the
visible channel, but the token counts now answer it: total generation is
unchanged, so nothing was switched off. The chain of thought was relocated.

- it is **not** a thinking-off arm, because total generation did not fall
- on cost it **is** effectively the `max` run, +1.3%, so it is a duplicate in
  everything except the reasoning-token label
- its scores are within noise of the `max` run, so it carries no information
  about reasoning effort

> **Corrected 2026-11-01.** This section previously read **+24%** on output
> tokens (5,630 against 4,546) and argued from that figure that the arm is "not
> a duplicate of the max run either, because it costs 24% more". Both numbers
> came from the `tokens_per_sample` column, which divides recorded usage by all
> 1000 rows; the max run had 179 cache-served rows reporting no usage, which
> deflated its mean and manufactured the gap. Recovered from the model events
> the difference is +1.5% on output and +1.3% on total, so the cost argument for
> treating the two as distinct does not hold. The conclusion that the arm
> carries no information about reasoning effort is unaffected, and the
> "relocated, not disabled" reading is now supported rather than merely
> possible.

Do not report it as an ablation. Its one legitimate use is as a rough
run-to-run variance estimate against the `max` run, and even that is imperfect
because the configurations differ.
