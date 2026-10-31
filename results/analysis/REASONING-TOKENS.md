# The monitor's hidden reasoning is already paid for, and it is a finer score than the one we ask for

Reproduce with:

```
uv run python scripts/analysis_reasoning_tokens.py \
  trajectories/dataset-haiku55-tm-n500-strip/trusted_monitoring
```

No API cost, but it needs a raw `.eval` log, which is gitignored. Measured on
the Haiku 5.5 trusted-monitoring run, n=500 honest and 500 attack on the same
500 problems.

## Why look

Reasoning models spend most of their output on tokens the caller never sees.
That raises two separate questions for a budget-indexed study, and they have
opposite answers.

## 1. Cost accounting: nothing is missing

`src/analyze.py` prices `output_tokens` and carried a comment asserting that
reasoning is included in it. That assertion is now checked rather than trusted.
On every sample in the run:

```
input_tokens + output_tokens + cache_write + cache_read == total_tokens
```

holds exactly, while `reasoning_tokens` is reported on top of that sum. So
reasoning is a subset of `output_tokens`, it is billed at the output rate, and
the dollar figures in `results/*.csv` are right. No correction is needed to any
cost or any cost-per-safety-point claim.

The measured share is worth recording anyway, because it is the real size of the
monitor's bill:

| arm    | reasoning tokens | visible tokens | reasoning share of output |
|--------|-----------------:|---------------:|--------------------------:|
| honest |              438 |            455 |                     49.1% |
| attack |              728 |            564 |                     56.4% |

53.4% of everything this monitor emitted was thinking, 583,255 tokens of
1,092,548. The headline figures circulating for the Artificial Analysis
Intelligence Index are higher, around 80% for this model. The gap is the task,
not the model: our monitor is asked to justify its score in prose, so it has an
unusually long visible output. A monitor prompted to emit a bare integer would
sit much closer to the headline number, and its dollar cost would be almost
entirely invisible.

Two practical consequences, both of which have already bitten this project:

- **`max_tokens` has to cover the thinking, not the answer.** The adversarial
  comments experiment first ran at `max_tokens=4000` and lost 61 of 250 samples
  to truncation, 20 on one arm against 47 on another. The loss was correlated
  with the arm, and in the direction of the hypothesis. It is now 16000 with
  retries and the loss is 2 to 3.
- **A zero is not proof of no reasoning.** The Qwen `effort=none` run reports
  `reasoning_tokens: 0` and genuinely did not think. GLM-5.3 with thinking
  disabled also reports 0, but relocates its chain of thought into the visible
  content (see `GLM-THINKING-TOGGLE.md`). The counter measures what the provider
  labels as reasoning, not whether reasoning happened.

## 2. Signal: the thing we were not recording is a score

The suspicion score is the bottleneck of this entire study. On this run it takes
**6 distinct honest values with 78.6% of honest rows at the mode**, so the
achievable audit budgets are 0.20%, 0.40%, 0.80%, 2.00%, and then 80.60%.
Nothing between 2% and 80.6% can be bought at any threshold (`SCORE-SCALE.md`).

Thinking length does not have that problem. It comes back on the same API
response at no extra cost, and it takes 363 distinct honest values with 0.8% at
the mode.

| signal                  |    AUC | distinct honest values | at mode |
|-------------------------|-------:|-----------------------:|--------:|
| suspicion score         | 0.8959 |                      6 |   78.6% |
| monitor reasoning tokens| 0.7564 |                    363 |    0.8% |
| monitor visible tokens  | 0.8119 |                    227 |    1.8% |
| prompt length           | 0.5410 |                    401 |    0.6% |

The monitor thinks measurably longer about backdoored code. Holding the problem
fixed by pairing the two arms on `sample_id`, the attack version draws **+290
reasoning tokens, 95% CI [+246, +335]**, and is longer on 79.6% of problems.

That is not program length talking. These backdoors are mostly independent
rewrites rather than edits, so an attack program could simply be bigger. Three
controls say it is not the explanation: prompt length on its own separates the
arms at AUC 0.5410, thinking residualised on prompt length with the fit taken
from honest rows only still reaches AUC 0.7482, and the paired comparison above
holds the problem exactly fixed. Thinking length is also close to independent of
the score it accompanies on the attack arm, Spearman +0.072.

### Using it to fill the void

Thinking length is a weaker classifier than the score, so it should not replace
it. Used to break ties *inside* the score's levels it costs nothing and loses
nothing: the tie-break weight is held below the smallest gap between distinct
score values, so the ordering is strictly lexicographic and no two samples the
score already separates can be reordered. The rank transform is fitted on honest
rows only, so the calibration never sees the attack arm.

That turns 6 operating points into 400, **301 of them inside the 2% to 80.6%
void where the score alone has none**.

| audit budget | score alone          | with the tie-break   |
|--------------|----------------------|----------------------|
| 1%           | 0.80% -> 57.0%       | 1.00% -> 60.4%       |
| 2%           | 2.00% -> 77.2%       | 2.00% -> 77.2%       |
| 5%           | 2.00% -> 77.2%       | 5.00% -> 79.0%       |
| 10%          | 2.00% -> 77.2%       | 10.00% -> 81.0%      |

AUC rises 0.8959 to 0.9146.

The recall gains are small, and they should be read as what they are. At a fixed
nominal budget the tie-break can only add thresholds between existing score
levels, so its recall is weakly higher **by construction**. A two-sided
confidence interval on a quantity bounded below by zero would be misleading, so
the paired bootstrap reports the sign instead, re-fitting the threshold on each
replicate:

| audit budget | median gain | positive in |
|--------------|------------:|------------:|
| 1%           |       +6.4% |       94.0% |
| 2%           |       +0.0% |       47.3% |
| 5%           |       +1.6% |       97.4% |
| 10%          |       +4.0% |      100.0% |

The 2% row is the control: the score can already buy exactly 2%, so there is
nothing for the tie-break to add and it adds nothing, 47.3% of replicates either
way. Where the score has no rung, the tie-break supplies one.

**The real result is not the extra recall. It is that an operating point exists
at all.** Comparing two protocols at 5% or 10% audit on this monitor was simply
not possible before, and reporting the 2% number as if it were the 10% number
overstates safety at 10% by crediting a budget that was never spent.

## Caveats

- **One run.** This is Haiku 5.5 at default effort. The other 30 runs' logs are
  gitignored and were not retained, so the finding cannot yet be checked across
  the monitor ladder or the effort ladder. `src/analyze.py` now writes
  `reasoning_tokens` into `results/*-samples.csv`, so every future run carries it
  without needing the log. Existing committed CSVs do not have the column.
- **Not a universal free lunch.** A monitor that does not reason, or one whose
  provider reports no count, has no tie-break available. Qwen at `effort=none`
  reports 0 on all 500 samples and would gain nothing.
- **Not validated as a standalone score.** AUC 0.7564 alone is well below the
  score, and the 1% row rests on a thin rung. The claim here is strictly about
  resolution, not about a better classifier.
- **Gameable in a way the score is not.** An attacker who knows thinking length
  is read has an obvious move: make the backdoor cheap to think about. Nothing
  here tests that, and it should not be deployed as a load-bearing signal
  without an adaptive-attacker arm.

## What this changes

Hidden reasoning tokens were already in the cost numbers, so no published figure
moves. The open item is the effort ladder: it is currently indexed by an opaque
provider label (`none`, `low`, `medium`, `high`, `xhigh`) and shows an inverted-U
on three monitors. Reasoning tokens are the dose that label is a proxy for, so
the ladder can be re-plotted against tokens actually spent and the inverted-U
tested against a real x-axis. That needs the per-run counts, which future runs
will now carry.
