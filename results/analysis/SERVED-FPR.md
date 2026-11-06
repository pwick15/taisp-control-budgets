# 92% of the study's safety cells are reported at a price they did not pay

Reproduce with:

```
uv run python scripts/analysis_achieved_fpr.py
```

No API cost. Full per-cell detail in `achieved-fpr.csv`.

## The question

Every safety number in this study is published against a **requested** audit
budget: 0.5%, 1%, 2%, 5%, 10%, 20%, 50%. A requested budget is not a rate, it is
a question, and each monitor answers it differently, because the threshold is a
percentile of its own handful of distinct honest scores applied with strict `>`.

So: if every cell were re-keyed on the rate it actually **served**, what shape
would the table be? The hope behind asking was that this is a relabelling job, a
few hours of axis work. It is not.

## The grid, over the 43 comparable n=500 runs

301 cells, 43 runs by 7 requested budgets.

| | |
|---|---|
| distinct served rates across the 301 cells | **51** |
| cells that served exactly the rate requested | **23 of 301 (8%)** |
| cells resting on at least 5 honest rows | 183 of 301 (61%) |

**Eight percent.** For the other 92%, the number in the column headed "safety at
2%" was bought at some other price, and which price depends on the monitor. The
table is not mislabelled by a rounding error; it is 51 different operating
points wearing 7 labels.

## Where the printable cells are

Printable means the cutoff rests on at least 5 honest rows, so the threshold is
estimated rather than placed on one or two observations.

| requested budget | runs with a printable cell | of |
|---|---|---|
| 0.5% | **0** | 43 |
| 1% | 12 | 43 |
| 2% | 30 | 43 |
| 5% | 34 | 43 |
| 10% | 35 | 43 |
| 20% | 36 | 43 |
| 50% | 36 | 43 |

The loss is positional, not uniform. **The cheapest column is empty for every
run in the study**, which follows from arithmetic rather than from monitor
quality: 0.5% of 500 honest samples is 2.5 rows, so no prompt and no score scale
can put 5 rows above a 0.5% cutoff. Only more honest samples can, and
`README.md` records why that is capped at 2,118 here.

The expensive end survives almost intact, which is the opposite of where a
control study wants its resolution.

## Seven runs lose every cell

| run | distinct honest scores | rates it can serve at all |
|---|---|---|
| `dataset-gemini35fl-high-tm-n500-strip` | 2 | 0.2% only |
| `dataset-gemini35fl-xhigh-tm-n500-strip` | 2 | 0.2% only |
| `dataset-gemini35fl-low-tm-n500-strip` | 3 | 0.2%, 0.4% |
| `dataset-gemini35fl-medium-tm-n500-strip` | 3 | 0.2%, 0.4% |
| `dataset-mistrallarge4-tm-n500-strip` | 4 | 0.2%, 0.4%, 0.6% |
| `dataset500-gemini35lite-tm-strip` | 4 | 0.2%, 0.4%, 0.8% |
| `dataset500-gemma426b-tm-strip` | 5 | 0.2%, 0.4%, 0.6%, 0.8% |

The two with two distinct honest scores are worth stating plainly: **their
published safety is the same number at all seven budgets.** Gemini 3.5
Flash-Lite at high recalls 0.190 at a 0.5% request and 0.190 at a 50% request,
because there is exactly one non-zero threshold available and asking for a
larger budget cannot buy a looser one. A seven-point budget sweep over that run
is one measurement printed seven times, on one honest row.

This is also the mechanism behind a claim that had to be withdrawn. The Gemini
ladder appeared to show reasoning *hurting* safety, thinking off reading 0.282
against xhigh's 0.186 at a 2% request. Off served that request at 0.8% FPR and
xhigh at 0.2%, so off was handed four times the audit budget. At 0.2%, the one
rate all five rungs serve exactly, the order reverses and more reasoning is
better: off 0.102, low 0.126, medium 0.150, high 0.190, xhigh 0.186.

## So what replaces it

Not a re-keyed table. A served-FPR frontier over these runs is **not
rectangular** and cannot be made so: 51 rates, no rate shared by all runs, and
the cheapest requested budget reachable by none of them. Relabelling the axis
would produce a grid with a different set of holes in every row.

The policy that follows, and that the rest of `results/analysis/` now uses:

1. **A cell is printable only if its cutoff rests on at least 5 honest rows.**
   Otherwise report the rate it can serve, not the rate requested.
2. **Label every cell with the rate it served**, never with the request. The two
   agree in 8% of cells.
3. **Compare two runs only at rates both serve exactly.** That is what
   `MATCHED-FPR.md` does, and it is why only 11 of 40 comparisons against Sonnet
   survive: the rest share no adequately powered rung, which is a fact about the
   monitors and not a gap in the analysis.
4. **Treat "no printable cell" as a result.** Seven runs cannot be placed on a
   budget axis at n=500. That is worth reporting about those monitors rather
   than hiding behind an interpolated number.

The scope correction is the deliverable here. This was estimated at three hours
of axis relabelling. It is a change to how every safety number in the project is
quoted, and the reason it is cheap in money and expensive in meaning is that the
data was always like this and the labels hid it.
