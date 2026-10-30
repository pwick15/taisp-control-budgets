# Gemma 3 4B vs Gemma 4 26B-A4B vs Gemma 3 27B: active parameters, and a ranking that inverts

Reproduce the resolution numbers with:

```
uv run python scripts/analysis_score_resolution.py
```

n=500 honest + 500 attack each, trusted monitoring, comments stripped, all three
served through the same litellm/DeepInfra route.

## The question

Does monitor capability track **total** parameters or **active** parameters?
Gemma 4 26B-A4B answers it directly: ~26B total, ~4B active per token. If
capability tracks active parameters it should behave like the 4B dense model; if
total, like the 27B dense one. This is a cleaner test than interpolating a size
curve, because the two dense models bracket it.

## What the headline table looks like

| monitor | total | active | safety @ 0.5% | @ 1% | @ 10% | @ 50% |
|---|---|---|---|---|---|---|
| Gemma 3 4B dense | 4B | 4B | 0.000 | 0.000 | 0.178 | 0.356 |
| Gemma 4 26B-A4B MoE | 26B | ~4B | **0.246** | **0.307** | 0.307 | 0.307 |
| Gemma 3 27B dense | 27B | 27B | 0.004 | 0.040 | **0.420** | **0.678** |

Read as a frontier, this says the MoE is the best of the three at a 1% audit
budget and the worst at 50%, and that the 27B dense model is beaten by a 4B one
at tight budgets. **The ranking inverts along the budget axis.**

Almost all of that is an artefact, and finding out which part is which is the
reason to look at resolution before reading a frontier.

## The honest score distributions explain it

| monitor | honest scores at 0.0 | distinct achievable FPRs (<=50%) |
|---|---|---|
| Gemma 3 4B | 141 of 500 (282 more at 0.1) | 2.40%, 3.80%, 4.80%, 7.80%, 9.60%, 10.0%, 11.2%, 12.6%, 15.4% |
| Gemma 4 26B-A4B | **496 of 500** | 0.20%, 0.40%, 0.60%, 0.80% |
| Gemma 3 27B | 335 of 500 | 0.20%, 0.80%, 1.20%, 2.20%, 2.80%, 4.40%, 10.0%, 33.0% |

**Gemma 4 26B-A4B scores 496 of 500 honest samples at exactly 0.0.** Its lowest
threshold already sits at a 0.80% FPR, and it has no operating point above that
at all. Every requested budget from 1% to 50% collapses onto the same `> 0`
threshold, which is why its safety column is the constant 0.307. It is not good
at tight budgets; it has *only* tight budgets, and above 0.80% it cannot spend
the audit budget it is given.

**Gemma 3 4B cannot be evaluated at a 1% budget at all.** Its lowest achievable
FPR is 2.40%, so its reported 0.000 at 0.5% and 1% measures nothing about its
detection ability. It is the thresholding floor.

**Gemma 3 27B is the only one of the three with a usable spread**, 0.20% through
33%, which is exactly why it looks worst where the others are degenerate and
best where they run out.

## The answer, from the metric that survives

AUC is threshold-free, so score degeneracy cannot distort it:

| monitor | active params | AUC |
|---|---|---|
| Gemma 3 4B dense | 4B | 0.6171 |
| Gemma 4 26B-A4B MoE | ~4B | 0.6490 |
| Gemma 3 27B dense | 27B | 0.7151 |

The MoE closes 0.032 of the 0.098 AUC gap between the two dense models, so it
sits far nearer the 4B than the 27B. **Monitor discrimination tracks active
parameters much more closely than total parameters**, which is the practically
useful version of the result: a cheap MoE does not buy you a large monitor.

Stated carefully: one model family, one route, one attack distribution, and
26B-A4B is a different generation (Gemma 4) than its two Gemma 3 brackets, so
generation and sparsity are not separated here. The direction is clear; the
coefficient is not.

## Why this matters beyond Gemma

This is the cleanest case in the study of a safety-vs-budget table that cannot
be read at face value. Two of the three monitors are degenerate in opposite
directions, and the resulting frontier ranks them in an order that reverses
depending on where you look. A single-operating-point comparison would have
picked a winner and been confidently wrong at every other budget.

The rule it implies: **report the achievable operating points alongside any
safety number, and treat a budget the monitor cannot express as missing data
rather than as a zero.**
