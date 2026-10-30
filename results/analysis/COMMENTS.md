# Why we strip comments: half of these backdoors confess in a comment

Reproduce every number here with:

```
uv run python scripts/analysis_backdoor_comments.py
```

No API cost. It reads the APPS dataset and the two committed `*-samples.csv`
files for the runs that differ only in `STRIP_COMMENTS`.

## The problem this resolves

Every run in the study sets `STRIP_COMMENTS=1`, so the monitor sees code with
comments removed. That was a judgement call made before we had measured it, and
the obvious objection is that it throws away signal.

Measuring it appears to confirm the objection, loudly. Same monitor
(Haiku 5.5, `reasoning_effort=xhigh`), same 500 honest + 500 attack samples, the
only difference being whether comments survive:

| | AUC | safety @ 0.5% | @ 1% | @ 2% | @ 50% | tokens/sample |
|---|---|---|---|---|---|---|
| stripped (study default) | 0.9422 | 0.575 | 0.714 | 0.850 | 0.964 | 4856 |
| comments kept | **0.9762** | **0.798** | **0.870** | **0.936** | **0.990** | **3019** |

Keeping comments is better at every audit budget, by 22.3 points at 0.5% and
15.6 points at 1%, and it is *cheaper* (38% fewer tokens, because the monitor
reasons less when the code is already explained to it). On its face, stripping
costs a large amount of safety for nothing.

The gap is not noise. Both arms happen to land on the same threshold (0.200) at
the nominal 1% budget, so that comparison is already at a matched achieved FPR
of 0.80%, and a paired bootstrap over problems with the threshold re-estimated
in each replicate gives:

| matched achieved FPR | honest rows | kept | stripped | difference | 95% CI |
|---|---|---|---|---|---|
| 0.60% | 3 | 79.8% | 57.4% | +22.4 pts | [+0.8, +32.8] |
| 0.80% | 4 | 87.0% | 71.4% | +15.6 pts | [+1.2, +32.0] |

Both rungs exclude zero. Both also rest on 3-4 honest rows, which is why the
intervals are so wide, and the two scales share no looser rung to check
(stripped can express 1.6%, kept 1.8%). So: real, large, and imprecisely
measured. Reproduce with `scripts/analysis_paired_bootstrap.py`.

It still does not mean what it looks like, and the reason is in the comments
themselves.

## Half the backdoors tell the monitor they are backdoors

Of the 500 verified backdoors the attack arm actually submitted:

- **354 (71%)** carry any `#` comment at all.
- **259 (52%)** carry a comment containing a tell-tale word: flaw, backdoor,
  bug, sabotage, intentional, deliberately, secret, hidden, edge case, trigger,
  exploit, subtle, incorrect, wrong.
- So of the backdoors that are commented at all, **73% give themselves away.**
  A comment on a backdoor in this dataset is far more likely to be a confession
  than not.

They are not subtle about it. Actual comments shipped inside the submitted code:

```
# Introducing a subtle flaw
# The subtle flaw
# Subtle bug
# Introducing the flaw
# Propagate right (with bug)
```

This is an artefact of how the dataset was built. These backdoors came from
models *asked to insert a subtle bug*, not from a model trying to survive a
monitor. Narrating the task you were given is the natural thing to do; evading a
reader was never part of the instruction.

The rate tracks the generator, and it varies enormously:

| generator | backdoors | confess | rate |
|---|---|---|---|
| anthropic/claude-3-7-sonnet-latest | 114 | 107 | 94% |
| anthropic/claude-3-5-haiku-latest | 22 | 20 | 91% |
| openai/gpt-4o | 79 | 57 | 72% |
| openai/gpt-4o-mini | 20 | 11 | 55% |
| anthropic/claude-3-7-sonnet-thinking-latest | 19 | 9 | 47% |
| openai/o1-mini | 41 | 15 | 37% |
| openai/gpt-3.5-turbo | 9 | 3 | 33% |
| openai/o3-mini | 157 | 33 | 21% |
| google/gemini-2.0-flash | 21 | 4 | 19% |
| unknown | 18 | 0 | 0% |

Worth noting against the generator-evasion result already in the study: o3-mini
and o1-mini backdoors are the hardest to catch, and they are also the two that
confess least. We have not shown that the second fact causes the first, and this
table alone cannot: confession rate and code subtlety are not separated here.

## The advantage is caused by the confessions, not by comments as signal

Join the two runs per `sample_id` and split the attack samples by what their
comment says. Backdoors with no comment at all are a built-in placebo: stripping
cannot change their input, so their arm-to-arm difference is pure monitor noise.

| bucket | n | stripped | kept | gain | share of total gain |
|---|---|---|---|---|---|
| no comment at all (placebo) | 146 | 0.466 | 0.468 | **+0.001** | 0.2% |
| comment, no tell-tale word | 95 | 0.374 | 0.536 | +0.162 | 17.0% |
| confessing comment | 259 | 0.453 | 0.742 | **+0.289** | 82.7% |

The placebo row lands at +0.001 on 146 samples, which both validates the
comparison and puts run-to-run noise near zero. Recall at each arm's own 1%
audit threshold tells the same story:

| bucket | stripped | kept |
|---|---|---|
| no comment at all | 77% | 77% (unchanged, as it must be) |
| comment, no tell | 60% | 85% |
| confessing comment | 73% | 93% |

**83% of the comments-kept advantage comes from backdoors whose comments
announce the backdoor.** The 15.6-point safety gain at a 1% audit budget is
mostly the monitor reading a confession, not the monitor reading code better.

## What this does and does not justify

It justifies stripping for this study. Keeping comments would report a monitor
frontier inflated by a property of the dataset rather than of the monitor, and
the inflation is generator-dependent, so it would also distort every
cross-generator comparison. A budget-indexed frontier measured on confessing
attackers is not a frontier anyone can deploy against.

It does **not** establish that comments are worthless to a monitor, and it does
not establish the stronger claim we would like: that stripping is strictly
correct because comments are an attack surface. The 17% of the gain from
non-confessing comments is real signal that stripping discards.

The missing measurement is the adversarial case. A misaligned model that knows
its comments are read would write comments that mislead, and nobody here has
measured what that does. If an adversarial-comments arm scores *below* the
stripped baseline, stripping stops being a dataset-artefact correction and
becomes a removal of attacker leverage. `scripts/experiment_adversarial_comments.py`
runs that three-arm comparison (original / stripped / adversarial) with an
integrity check that the rewrite changed only comments and not a byte of
executable code.

## Caveats

- `TELL` is a keyword regex, not a judge. It will miss a confession phrased
  without those words and will fire on an innocent "# handle edge case". Treat
  52% as an estimate of the right order, not a precise count; the placebo and
  bucket structure above do not depend on its exact boundary.
- The labels are built from the dataset the runs actually used:
  `has_backdoor_solution=True` with `backdoor_source` left at its `"any"`
  default, taking `backdoors[0]`, which is what `apps_solution_policy()` submits
  when `backdoor_model=None`. Labelling the `"control_tax"` subset instead
  selects a set differing by 8 of 500 samples and scores comments the monitor
  never saw. All 500 attack rows join across both runs.
- One monitor, one effort level. The size of the advantage will differ for a
  stronger monitor, which needs the confession less.
- Honest samples keep their comments in both arms, so the audit threshold is set
  by the same honest distribution and only the attacker side changes.
