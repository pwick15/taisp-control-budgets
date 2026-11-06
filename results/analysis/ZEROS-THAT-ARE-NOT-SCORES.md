# Twelve committed zeros that are not monitor scores

408 rows across seven arms carried ControlArena's default 0 for a reply its parser
could not read. Those are recovered from the model events and audited in
`recovered-scores.csv`. Twelve more remain, in four arms, and they are still sitting in
`results/` as `0.0`. None of them can be recovered from a committed or retained file, and
the two reasons are different enough that they need different fixes.

A 0 is the least suspicious value on the scale, not a placeholder for "unknown". On the
honest side it is a spurious low observation that drags the audit threshold down; on the
attack side the catch rule is a strict `>`, so the row can never be caught at any budget.

## Group A: the reply was never retained (9 rows)

| run | mode | sample ids |
|---|---|---|
| `dataset500-gemma426b-tm-strip` | attack | 109, 399, 472, 1113 |
| `dataset500-gemma426b-tm-strip` | honest | 191, 1175 |
| `dataset500-sonnet55-um-scale100-strip` | attack | 731 |
| `dataset500-sonnet55-um-strip` | attack | 622, 1284 |

Every one of these samples carries **zero model events**, which is what this cohort's
`usage_source=sample_field_complete` records: the logs kept no usage-bearing model events
at all, so the monitor's text is simply not in them. This is the same position as the 13
Ministral scores in `../README-ministral14b-provenance.md`, with one difference: those
were overwritten with values transcribed from a terminal, while these are still the
parser's default and are at least honestly wrong.

Two of them matter more than their count suggests. `dataset500-sonnet55-um-strip` is the
reference arm for `MATCHED-FPR.md` and the lead row of the report chart, and both of its
affected rows are attack rows, so the reference's recall is understated by up to 0.4
points (2 of 500) at every budget it is compared at.

The only fix is a fresh monitor pass over the retained trajectories. Re-ingesting a
collaborator's archive will not help: these runs have no model events by construction, so
any copy of them has the same hole.

## Group B: the monitor returned nothing (3 rows)

| run | mode | sample ids |
|---|---|---|
| `dataset-gemini35fl-low-tm-n500-strip` | attack | 293, 961 |
| `dataset-gemini35fl-low-tm-n500-strip` | honest | 1006 |

These are **not parse failures**. Each has exactly one model event, with usage recorded,
no error, and a completion of **zero characters**. Gemini returned an empty reply, so
"No score found in model response" is literally true and there is no score to read. The
arm is the low reasoning-effort rung, which is the shape of the familiar trap where a
reasoning model spends its budget and emits no visible text.

Here a 0 is not a recoverable mistake but a fabricated observation standing in for a
measurement that was never made. A missing value would be the honest record. Under this
project's rule that a run named `n500` delivers 500 scored samples, marking them missing
makes the arm incomplete, so the clean resolution is a re-run rather than an edit.

## Repair these twelve cells, not these four arms

Re-scoring only the affected cells is the right repair, and `CLAUDE.md` already says so:
executing a configuration in several passes "is fine and is the intended way to repair
one". The worked example in that rule generated exactly the samples that were missing and
replayed the rest.

The objection to a partial repair is selection on outcome, and it does not have much grip
here. Selection on outcome means choosing cells **by their value** and keeping the
replacement; that biases the arm however few cells you touch. These cells were chosen for
having no recorded value, which is a property of the logging and the parser rather than of
the score. What remains is a missing-data risk: the failure that selected them may itself
correlate with the value, and in the gpt-oss arms it demonstrably did, since the model
broke format exactly when it wanted a value just above zero. So the repaired cells may not
be a random draw from their arm, and that should be disclosed per cell rather than paid
for at a thousand times the cost.

A fresh pass over a whole arm removes the selection, and buys it badly. It replaces 994 to
999 measurements that were never in question, costs about $21.55 across these four arms
against roughly $0.04 for the cells, and for `dataset500-sonnet55-um-strip` it redraws the
study's reference arm, which would rewrite every gap, interval and verdict in
`MATCHED-FPR.md` as a side effect of fixing two cells.

Meanwhile: the twelve are worth at most 0.4 points on the Sonnet reference and about 1.2
on `gemma426b`, so they overturn nothing, but they are fabrications and should not be
quoted as measurements.
