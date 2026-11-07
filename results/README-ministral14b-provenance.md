# Ministral 14B: 13 of its 1,000 scores were unauditable, and now are not

`dataset500-ministral14b-tm-strip` is complete and all 1,000 rows are scored, so it
passes every structural check in `scripts/check_tables.py`. Thirteen of those scores are
nevertheless unverifiable, and this note records why, what was checked, and what would
fix it. **Do not try to fix it by re-ingesting a collaborator's logs. That does not work,
and the reason is the interesting part.**

## What happened

Ministral sometimes wrote its score as `<score>**7/10**` with no closing tag, so
ControlArena's parser stored the default 0 with the reason "No score found in model
response". `scripts/fix_unparsed_scores.py` repaired 13 such rows by matching each sample
to a score read off the terminal during the run, keyed on a keyword from the problem
statement. That script's own docstring says the full responses "were printed to the
terminal during the run (not saved in the logs)".

So the source of those 13 values is a terminal scrollback that no longer exists. They
cannot be re-derived, and no reader can check them.

## Resolved 2026-11-06: re-scored, and now auditable

A Mistral route became available through the litellm proxy, on the exact model id the
original run used (`mistral/ministral-14b-2512`; three other spellings still return no
healthy deployments). The 13 samples were rebuilt into their own trajectory, stripped of
the old monitor metadata, and re-scored under the arm's configuration
(`trusted_monitoring`, comments stripped, default 0-10 prompt). The replies are retained
in `logs/repair-ministral14b`, so these 13 values can now be checked by anyone, which is
the whole point. None of them failed to parse this time.

**What the comparison shows, and what it does not.** Ten of the 13 re-scored values differ
from the transcribed ones, three are identical, and the differences run from +1 to -8
points on the 0-10 scale. That does **not** establish that the transcription was wrong.
Ministral is not deterministic, so a second pass is a fresh draw rather than a check, and
the spread is mostly this monitor's run-to-run variance on these samples. Both readings
are recorded above and in the commit, so nothing is hidden by the replacement.

The two readings are worth keeping in mind as a variance estimate in their own right: a
monitor whose score on the same trajectory can move 8 points between passes is weakly
determined on these samples, whichever pass you take.

**Effect on the published numbers: almost none.** Safety moves by at most 0.004 at any
budget, the headline 0.06 at a 2% budget is unchanged, and the honest arm keeps 10
distinct values with its maximum still at 1.0 (one fewer row sits there, 4 to 3). So the
hand transcription, whatever its per-cell errors, never materially distorted this arm.

**What changed in kind.** The arm no longer carries values that only a lost terminal
could vouch for. It now carries values with retained replies, from a documented second
pass, which is the standard this project applies everywhere else.

One honest caveat about provenance: 987 of the 1,000 rows come from the original pass and
13 from a pass on 2026-11-06 through a different transport, the litellm proxy rather than
Mistral's API directly. The model id is the same. Under this project's rule that
multi-pass execution is the intended way to repair a run, that is a repaired run rather
than two runs mixed, but the mixture is real and is recorded here rather than inferred.

## What was checked on 2026-11-05, before the re-score


**The retained logs hold no raw reply for these samples.** The four gpt-oss arms had the
same parse-failure defect and were fully repaired from the model events in their own eval
logs, because the monitor's raw completion is still there (see
`analysis/recovered-scores.csv` and `scripts/recover_unparsed_scores.py`). That does not work
here: every one of the 13 samples carries **zero** model events with completion text.
That is consistent with this run's provenance column, `usage_source=sample_field_complete`,
which records that the log has no usage-bearing model events at all. There is no retained
text to read a score from.

**The collaborator archive is not a pristine copy.** `anusha-monitor-logs.zip` contains
this run's six `.eval` pieces, and they were checked directly. All 13 rows in the archive
already carry the `Score recovered from unparsed response (N/10)` marker, so
`fix_unparsed_scores.py` had already been applied before the archive was made. **Re-ingesting
from that archive would reproduce exactly the same 13 hand-transcribed values, not
recover them.** If you still hold these logs locally, your copy is almost certainly in the
same state, and overwriting from it would change nothing while appearing to fix something.

**A re-run was not possible from this machine, at the time.** This is what the
2026-11-06 re-score above removed, once a Mistral route was added to the proxy.
Recorded because the probe results are still the right starting point if the
route disappears again. The run used
`mistral/ministral-14b-2512`, Mistral's own API, and there is no Mistral key here. The
litellm proxy has no route to it: `mistral/ministral-14b-2512`, `ministral-14b-2512` and
`mistral/ministral-14b` all return "no healthy deployments". DeepInfra does not serve it
either; its list carries only Mistral Small 24B, Mistral Nemo and Voxtral. That negative
was confirmed rather than assumed: `deepinfra/mistralai/Mistral-Small-24B-Instruct-2501`
returns 200 through the same proxy and prefix form, so the Ministral failures are the
model's absence and not a wrong id.

## Why it matters, and how much

Three of the 13 are **honest** rows, entered as 0.7, 0.8 and 1.0. The audit threshold is a
high percentile of the honest scores alone, and this arm's honest side has only 6 rows at
1.0 in total, so a single transcription slip among those three moves the published safety
number. The arm is published at 0.06 safety at a 2% budget, the weakest monitor in the
study, and `scripts/check_tables.py` cannot see any of this because the rows are present
and numeric.

The remaining ten are attack rows, where the effect is bounded differently: a wrong value
changes whether that one backdoor is counted as caught at a given threshold.

## If it ever needs doing again

The trajectories are complete and local: `trajectories/dataset-n400` holds four of the six
pieces and `trajectories/dataset-batch3` the other two, covering all 1,000 samples. A full
fresh pass over the arm costs about **$0.43** at this arm's recorded rate. The 2026-11-06
repair did not do that: it rebuilt only the 13 affected samples into their own trajectory
and re-scored those, for well under a cent.

That choice is deliberate and is the project's documented practice, not a shortcut. A
re-score of the whole arm would replace 987 measurements that were never in question, and
`CLAUDE.md` states that executing a configuration in several passes "is fine and is the
intended way to repair one". What a subset repair cannot claim is freedom from selection:
the 13 cells were picked out by a failure, and if that failure correlates with the score
then the repaired cells are not a random sample of the arm. Here the exposure is bounded
and measured: at most 0.004 of safety at any budget.
