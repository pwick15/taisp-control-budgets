# Trajectories received from Anusha, 2026-10-30

Extracted from `anusha-trajectories.zip`. **Left untracked on purpose**: see the
size note at the bottom.

| directory | files | samples per file | size | what it is |
|---|---|---|---|---|
| `dataset-batch3/untrusted/` | 2 | 100 | 44M | dataset policy, honest + attack |
| `dataset-n400/untrusted/` | 4 | 200 | 116M | dataset policy, two batches of 200 (400 problems) |
| `model-sonnet55-n10/` | 3 | 10 | 576K | model policy: trusted honest, untrusted honest + attack |

All open cleanly with `read_eval_log`. Policy model reads `none/none` on the
dataset runs, which is expected: `apps_solution_policy` submits stored
solutions and makes no model calls.

`model-sonnet55-n100` was also in the archive and was **not** copied: its three
files are byte-identical (md5) to the three already committed under
`trajectories/model-sonnet55-n100/`.

## Why these are not committed

160MB of new `.eval` files. Whether trajectories belong in git is still an open
decision (see the tracking note): the full local set is ~2.3GB, git-lfs is not
set up here, and GitHub rejects files over 100MB. These particular files are all
under 50MB each so they *could* go in, but adding 160MB to the repo is a call
for the team, not a side effect of unpacking an archive.

Nothing is lost either way: the archive is still at
`~/workspace/anusha-trajectories.zip`.

## Using them

They are in the layout `src/monitor.py` expects, so they can be scored with a
new monitor without re-running any policy:

```bash
TRAJ_DIR=trajectories/dataset-n400 MONITOR_MODEL=anthropic/claude-haiku-5-5 \
  uv run python src/monitor.py
```

The `dataset-n400` set is the interesting one: 400 dataset-policy problems,
against the 500 the rest of the study uses, so sample ids will only partly
overlap. Check the overlap before pooling it with existing results.
