# Ministral 14B: 13 of its 1,000 scores cannot be audited

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

## What was checked, 2026-11-05

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

**A re-run is not possible from this machine.** The run used
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

## What would resolve it

A fresh monitor pass over the retained trajectories, which are complete and local:
`trajectories/dataset-n400` holds four of the six pieces and `trajectories/dataset-batch3`
the other two, covering all 1,000 samples. At the rate recorded for this arm,
$0.0004305 per sample, that is about **$0.43**. It needs a Mistral API key, or for whoever
has one to run it:

```
TRAJ_DIR=trajectories/dataset-n400   MONITOR_MODEL=mistral/ministral-14b-2512 \
  STRIP_COMMENTS=1 LOG_DIR=logs/dataset500-ministral14b-tm-strip-v2 \
  uv run python src/monitor.py
TRAJ_DIR=trajectories/dataset-batch3 MONITOR_MODEL=mistral/ministral-14b-2512 \
  STRIP_COMMENTS=1 LOG_DIR=logs/dataset500-ministral14b-tm-strip-v2 \
  uv run python src/monitor.py
```

That is a fresh draw over all 1,000 samples, not a repair of 13, so it would be a new
execution of the configuration. Under this project's rule that exactly one execution is
"the run", the complete one, it would replace this arm and this one would move to
`results/superseded/` with a note. Re-scoring only the 13 affected samples would be
selection on outcome and is not an option.

Until then, treat Ministral 14B's safety figures as carrying 13 rows of unaudited
provenance, and do not cite this arm as a precise number without saying so.
