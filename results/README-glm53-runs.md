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

Over the 500-problem run: `none` used **5,630 output tokens/sample against the
default's 4,546 (+24%)** and reported **no reasoning tokens at all**, yet scored
the same (0.760 vs 0.762) with an identically-sized parsed `<reasoning>` block
(~1,826 characters in both).

Those extra ~5,180 tokens per sample are not in the parsed reasoning field. The
harness stores only the parsed `MonitorResponse`, not the raw completion, so
**we cannot tell from the logs whether thinking was disabled or merely moved
into the visible channel and then discarded by the parser.** Either way:

- it is **not** a thinking-off arm, because total generation went up, not down
- it is **not** a duplicate of the `max` run either, because it costs 24% more
  and reports usage differently
- its scores are within noise of the `max` run, so it carries no information
  about reasoning effort

Do not report it as an ablation. Its one legitimate use is as a rough
run-to-run variance estimate against the `max` run, and even that is imperfect
because the configurations differ.
