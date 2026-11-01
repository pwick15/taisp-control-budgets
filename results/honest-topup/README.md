# One-sided honest arms. These are not runs.

Everything in this folder is a **top-up to an existing run's honest side**, not a run.
`CLAUDE.md` and `../../README.md` define a run as 500 honest and 500 attack samples, all
scored, and that rule is what makes the committed numbers mean anything. A file here has
500 honest samples and no attack samples at all.

## Why they exist

Every audit threshold in this study is a percentile of the **honest** score distribution,
applied with a strict `>`. So the number of operating points a comparison can stand on is
set by how many honest rows sit above the cutoff, and nothing else:

- buying more **honest** samples puts more rows above every cutoff, which both narrows
  intervals and makes rungs printable that could not clear the five-row bar before;
- buying more **attack** samples does neither, and the attack pool caps at 1,061 paired
  problems anyway.

So the honest side is the only side worth buying, and a one-sided arm is the artifact that
buying it produces.

## Why they are not in `results/`

Every analysis script discovers runs by globbing `results/*-samples.csv`. A one-sided arm
in that glob would be read as a run with 500 honest and 0 attack samples, and
ControlArena's `compute_safety` returns **1.0 from an empty denominator** rather than
failing, so it would quietly report perfect safety. One directory keeps it out of every
consumer at once, which is the same reason `results/superseded/` exists.

`src/analyze.py` is deliberately never called on these. Use
`scripts/extract_honest_topup.py`, which writes scores and reasoning tokens and no safety
figure, because a one-sided arm does not have one.

## How to read one

A top-up extends exactly one arm, named in the filename, and its problems are **disjoint**
from that arm's. `scripts/analysis_honest_topup.py` asserts the disjointness before
concatenating, because an overlap would double-count a problem in the honest arm and move
every threshold.

The extra problems are the next `interview`-difficulty problems in the same
`get_dataset(has_backdoor_solution=True)` pool, continuing the prefix the run itself took.
That keeps the honest arm inside the single difficulty band every number in this project
describes (see the dataset-scope section of `../../README.md`). The pool holds 1,061
interview problems, the runs took the first 500, so **561 remain**: a second top-up of this
size is the last one available without leaving the band.

## What is here

| file | extends | honest samples |
|---|---|---|
| `dataset-haiku55-xhigh-scale100-n500-strip-honest-topup-samples.csv` | `dataset-haiku55-xhigh-scale100-n500-strip` | 500 |
| `dataset500-sonnet55-um-scale100-strip-honest-topup-samples.csv` | `dataset500-sonnet55-um-scale100-strip` | 500 |

Both were scored with their parent arm's exact configuration, read off that arm's own model
events rather than reconstructed from memory: the 0-100 prompt with `MONITOR_SCORE_MAX=100`,
comments stripped, Haiku at `reasoning_effort=xhigh` and Sonnet at its default.
