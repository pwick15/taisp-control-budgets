"""Choose which problems a honest-side top-up should score, reproducibly.

    uv run --with datasets python scripts/pick_honest_topup_ids.py [N] [OUT]

Writes a JSON list of dataset sample ids, default 500 to
results/honest-topup/topup-ids.json, for `SAMPLE_IDS` in src/experiment.py.

Why the ids are chosen rather than taken
----------------------------------------
`shuffle_dataset` is False, so a bare `limit` takes a prefix. That is what makes every run
in this project a nested prefix of one difficulty band: the eligible pool holds 1,061
`interview`, 277 `introductory` and 106 `competition` problems, and the first 500 are 100%
interview. Extending an arm by raising the limit would therefore re-score the 500 it
already has AND pull in a different difficulty mix, changing the population as well as its
size. Naming the ids avoids both.

The choice is the next `interview` problems after the ones already scored, continuing the
same prefix in the same pool. 561 remain, so one top-up of 500 is the last one available
without leaving the band. Difficulty is not in the metadata the control-arena loader
exposes, so it is joined from the source dataset's own `difficulty` column by problem id.
"""
import json
import sys
from pathlib import Path

DEFAULT_N = 500
DEFAULT_OUT = Path("results/honest-topup/topup-ids.json")
ALREADY_SCORED = 500   # the prefix every n=500 run took
BAND = "interview"


def main() -> None:
    n = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_N
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    from datasets import load_dataset
    from control_arena import EvalMode
    from control_arena.settings.apps.task.dataset import get_dataset

    src = load_dataset("RoganInglis/apps-control-arena", split="train")
    difficulty = {str(r["problem_id"]): r["difficulty"] for r in src}

    # The same filters src/experiment.py applies under POLICY=dataset, so the pool and its
    # order are the ones every run in scope saw.
    pool = [str(s.id) for s in get_dataset(has_backdoor_solution=True,
                                           backdoor_source="any", mode=EvalMode.ATTACK)]
    unlabelled = [i for i in pool if i not in difficulty]
    if unlabelled:
        sys.exit(f"{len(unlabelled)} pool ids have no difficulty label; refusing to guess")

    scored, rest = pool[:ALREADY_SCORED], pool[ALREADY_SCORED:]
    band_scored = {difficulty[i] for i in scored}
    if band_scored != {BAND}:
        sys.exit(f"the first {ALREADY_SCORED} are {sorted(band_scored)}, not all {BAND}; "
                 f"this script's premise no longer holds")
    candidates = [i for i in rest if difficulty[i] == BAND]
    pick = candidates[:n]
    if len(pick) < n:
        sys.exit(f"only {len(candidates)} {BAND} problems remain past the first "
                 f"{ALREADY_SCORED}; asked for {n}")
    assert not set(pick) & set(scored), "picked a problem the runs already scored"

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(pick, indent=0) + "\n")
    print(f"pool {len(pool)}: " + ", ".join(
        f"{k} {sum(1 for i in pool if difficulty[i] == k)}"
        for k in sorted({difficulty[i] for i in pool})))
    print(f"first {ALREADY_SCORED} are all {BAND}; {len(candidates)} {BAND} problems remain")
    print(f"wrote {out}: {len(pick)} ids, {pick[0]} to {pick[-1]}, "
          f"{len(candidates) - len(pick)} still unused")


if __name__ == "__main__":
    main()
