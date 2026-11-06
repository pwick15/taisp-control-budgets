"""Build a trajectory holding only the samples of a run that need re-scoring.

    uv run python scripts/build_repair_trajectory.py <run> <out-dir> '<reason-regex>'

    # the three Gemini cells whose monitor returned an empty reply
    uv run python scripts/build_repair_trajectory.py \
      dataset-gemini35fl-low-tm-n500-strip \
      trajectories/repair-dataset-gemini35fl-low-tm-n500-strip \
      'No score found in model response'

Why this exists. A handful of cells across the study hold ControlArena's parse-failure
default rather than a measurement, and the monitor's reply was not retained, so they
cannot be recovered with `scripts/recover_unparsed_scores.py` and have to be measured
again. Re-running a whole arm to fix one cell would replace 999 measurements that were
never in question, cost a thousand times as much, and for the reference arm would rewrite
every comparison in `MATCHED-FPR.md` as a side effect. `CLAUDE.md` is explicit that
executing a configuration in several passes "is fine and is the intended way to repair
one", so this takes the affected samples out into their own trajectory and nothing else
is touched.

What it does. Copies the matching samples into `<out-dir>/untrusted/`, which is the layout
`src/monitor.py` expects, and strips the previous monitor pass off them so the monitor
scores them fresh: the `suspicion_score`, `reason` and `model_usage` keys come off the
message metadata, `max_suspicion_scorer` comes off the sample, and `model_usage` is
cleared. That is the same stripping `scripts/build_hard51.py` does, with one deliberate
difference noted below.

A caveat that has already caused one near-miss. Like build_hard51.py, this leaves
`sample.events` alone, so a sample can still carry the model event of an earlier pass.
On the Opus hard51 arms that event belongs to the Haiku run that produced the trajectory
and ends in a well formed `<score>1</score>`, which is why
`scripts/recover_unparsed_scores.py` refuses to read a reply whose model is not the arm's
own monitor. Do not read a score out of a trajectory built by this script; re-score it.

Then: run src/monitor.py over the output with the arm's original configuration, and splice
the results back. The arm's configuration is not recorded in its eval log, so it has to
come from the run name and the committed `tokens_per_sample`.
"""
import glob
import re
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log, write_eval_log

MONITOR_KEYS = ("suspicion_score", "reason", "model_usage")
SCORER = "max_suspicion_scorer"


def main() -> int:
    if len(sys.argv) != 4:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    run, out_dir, pattern = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    rx = re.compile(pattern)
    paths = sorted(glob.glob(f"logs/{run}/*/*.eval"))
    if not paths:
        sys.exit(f"no eval logs under logs/{run}/*/")
    (out_dir / "untrusted").mkdir(parents=True, exist_ok=True)
    total = 0
    for p in paths:
        log = read_eval_log(p)
        keep, ids = [], []
        for s in log.samples or []:
            if not any(rx.match(str((getattr(m, "metadata", None) or {}).get("reason") or ""))
                       for m in s.messages):
                continue
            for m in s.messages:
                md = getattr(m, "metadata", None)
                if md:
                    for k in MONITOR_KEYS:
                        md.pop(k, None)
            if s.scores:
                s.scores.pop(SCORER, None)
            s.model_usage = {}
            keep.append(s)
            ids.append(str(s.id))
        if not keep:
            continue
        log.samples = keep
        if log.results:
            log.results.total_samples = len(keep)
            log.results.completed_samples = len(keep)
        dest = out_dir / "untrusted" / Path(p).name
        log.location = str(dest)
        write_eval_log(log, str(dest))
        total += len(keep)
        print(f"  {Path(p).name[:56]:58s} kept {len(keep):2d}: {','.join(ids)}")
    print(f"wrote {total} sample(s) to {out_dir}/untrusted")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
