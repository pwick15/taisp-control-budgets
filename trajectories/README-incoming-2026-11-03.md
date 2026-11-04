# Monitor logs received from collaborators, 2026-11-03

Four archives, two sent for review and two already on disk. All of it is
git-ignored (`logs*/`, `trajectories/**/*.eval`); this file is the record of what
arrived and what was taken from it, so the question "what happened to my logs"
has an answer in the repository rather than in someone's notes.

| archive | size | eval files | taken |
|---|---|---|---|
| `pj-trajectories-v2.zip` | 688 MB | 12 | 2 new runs, 4 gap-filling, 0 discarded |
| `anusha-monitor-logs.zip` | 1.33 GB | 62 | 2 new runs, 8 gap-filling, 1 superseded, 5 smoke |
| `anusha-trajectories.zip` | 183 MB | 12 | policy trajectories; 2 of 3 directories already held |
| `punji-traj.zip` | 344 MB | 4 | **nothing** |

`punji-traj.zip` holds only `dataset-haiku55-tm-n500-strip` and
`dataset-qwen38omniflash-none-tm-n500-strip`, and both are byte-identical to the
same runs in `pj-trajectories-v2.zip`. It is a strict subset, so counting it
would have double-counted four files. Likewise `anusha-trajectories.zip`'s
`dataset-batch3` and `dataset-n400` were already held at identical file count and
size.

## Placement

- `logs/<run>/` the analysable monitor runs, 21 directories added.
- `logs/smoke/` n=1 to n=10 tests (`mock`, `gemini-ministral-tm`,
  `sonnet55-n10-haiku45-strip`), below any scope and excluded by name.
- `logs-superseded/dataset400-sonnet55-um-strip` is n=400, and all 400 of its
  honest ids are among the 500 of `dataset500-sonnet55-um-strip`. With
  `shuffle_dataset=False` a smaller run is a **prefix** of a larger one, so it is
  a nested subset rather than an independent sample and must never be compared or
  averaged against it.
- `trajectories/model-sonnet55-n10-anusha` policy trajectories.

## Two things worth knowing about these logs

**Eight of the runs carry no usage-bearing model events**, only the sample-level
`model_usage` field, because they were recorded by a record-once monitor-many
pass. That field covers every sample in each of them, and Inspect empties it for
a call it serves from cache, so full coverage is the evidence that none was
cached and the totals are complete rather than a lower bound. `usage_source`
records this per run as `sample_field_complete`; see the provenance table in
README.md.

**Several runs arrived as multiple passes of one arm.** `analyze.py` sums them,
and refuses only when the same (arm, problem) appears in two logs, because
disjoint passes of one arm are exactly what a repair pass produces. The
`dataset500-sonnet55-um-strip` logs are three such passes over sample ids 7 to
631, 632 to 1118 and 1119 to 1324, with no overlap.
