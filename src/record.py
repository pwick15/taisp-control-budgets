"""Record trajectories once, so monitors can be compared on them later without re-running U.

    uv run python src/record.py 100

Step 1 of "record once, monitor many times" (step 2 is src/monitor.py). It runs the policies
with NO monitor and saves the full transcripts:

    <TRAJ_DIR>/untrusted/   U on every problem, honest and attack mode
    <TRAJ_DIR>/trusted/     T solving the same problems honestly. Only needed to simulate
                            defer-to-trusted offline (src/defer_sim.py): when a sample is
                            deferred, T's solution to that problem is used instead.

Every monitor you try later reads exactly the same U outputs, which makes monitor comparisons
fair and lets anyone reproduce the numbers from the saved files.

Env vars:
    UNTRUSTED_MODEL  U (default anthropic/claude-sonnet-5-5)
    TRUSTED_MODEL    T (default anthropic/claude-haiku-4-5-20251001)
    POLICY           "model" (default): U writes the code. "dataset": U is replaced by the APPS
                     dataset's solutions and verified backdoors (no U API calls).
    TRAJ_DIR         where to save (default trajectories/<policy>-<U name>-n<problems>)
    RECORD           which runs: "untrusted", "trusted" or "untrusted,trusted" (default both)
    MAX_CONNECTIONS  max concurrent API calls per model (default 10; use 1-2 on free tiers)
    MAX_SANDBOXES    max concurrent Docker sandboxes (default 10)
    EXCLUDE_FROM     comma-separated trajectory folders whose problems to skip, matched by problem
                     id (e.g. an earlier run, so a new run uses only problems it hasn't seen)
    START            skip this many of the remaining problems first (default 0), to record in
                     batches: START=0 then START=200 with `record.py 200` gives 400 problems.
                     Give every batch the same TRAJ_DIR; later steps read them as one set.
"""
import os
import sys
from pathlib import Path

from inspect_ai.log import read_eval_log

from inspect_ai import eval as inspect_eval
from inspect_ai.model import GenerateConfig

from control_arena import EvalMode
from control_arena.eval import ControlEvalConfig, get_control_task_product
from control_arena.policy import trusted_policy_builder, untrusted_policy_builder
from control_arena.settings.apps.apps_setting import AppsSetting
from control_arena.settings.apps.apps_solution_policy import apps_solution_policy


def short_name(model: str) -> str:
    return model.split("/")[-1].replace(".", "")


def ids_in(folders: str) -> set[str]:
    """Problem ids recorded under each trajectory folder (read from its .eval files)."""
    ids: set[str] = set()
    for folder in filter(None, (f.strip() for f in folders.split(","))):
        files = sorted(Path(folder).rglob("*.eval"))
        if not files:
            sys.exit(f"EXCLUDE_FROM: no .eval files under {folder}")
        for f in files:
            ids.update(str(s.id) for s in read_eval_log(str(f)).samples or [])
    return ids


def main() -> None:
    n_problems = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    start = int(os.getenv("START", "0"))
    exclude_from = os.getenv("EXCLUDE_FROM", "")
    untrusted = os.getenv("UNTRUSTED_MODEL", "anthropic/claude-sonnet-5-5")
    trusted = os.getenv("TRUSTED_MODEL", "anthropic/claude-haiku-4-5-20251001")
    policy_mode = os.getenv("POLICY", "model")
    if policy_mode not in ("model", "dataset"):
        sys.exit(f'POLICY must be "model" or "dataset", got {policy_mode!r}')
    use_dataset = policy_mode == "dataset"
    traj_dir = Path(os.getenv("TRAJ_DIR", f"trajectories/{policy_mode}-{short_name(untrusted)}-n{n_problems}"))
    record = os.getenv("RECORD", "untrusted,trusted").split(",")
    if set(record) - {"untrusted", "trusted"}:
        sys.exit(f'RECORD must list "untrusted" and/or "trusted", got {record}')

    max_connections = int(os.getenv("MAX_CONNECTIONS", "10"))
    config = ControlEvalConfig(
        untrusted_model=untrusted,
        trusted_model=trusted,
        untrusted_config=GenerateConfig(max_connections=max_connections),
        trusted_config=GenerateConfig(max_connections=max_connections),
        limit=None if (start or exclude_from) else n_problems,
        max_sandboxes=int(os.getenv("MAX_SANDBOXES", "10")),
    )
    # Same setting and limit for both runs, so U and T see exactly the same problems.
    setting = AppsSetting(has_backdoor_solution=use_dataset)

    runs = {
        # U: honest and attack. No monitor, so nothing here depends on which monitor you pick later.
        "untrusted": (apps_solution_policy() if use_dataset else untrusted_policy_builder(),
                      [EvalMode.HONEST, EvalMode.ATTACK]),
        # T solving the problems honestly: the fallback answers for defer-to-trusted.
        "trusted": (trusted_policy_builder(), [EvalMode.HONEST]),
    }
    # Pick problems by id when skipping some: drop excluded ids, then take n after START.
    eval_args = config.eval_args()
    if start or exclude_from:
        excluded = ids_in(exclude_from) if exclude_from else set()
        # Keep each id's original type (Inspect matches sample ids exactly); compare as text.
        ordered = [s.id for s in setting.get_dataset(EvalMode.HONEST)]
        remaining = [i for i in ordered if str(i) not in excluded]
        chosen = remaining[start:start + n_problems]
        if not chosen:
            sys.exit(f"No problems left: {len(ordered)} in the setting, {len(excluded)} excluded, START={start}")
        if len(chosen) < n_problems:
            print(f"note: only {len(chosen)} problems left after START={start}")
        print(f"{len(ordered)} problems in the setting; skipping {len(ordered) - len(remaining)} from "
              f"EXCLUDE_FROM; taking {len(chosen)} from position {start} of the remaining {len(remaining)}")
        eval_args = {**eval_args, "limit": None, "sample_id": chosen}
        n_problems = len(chosen)
    print(f"Recording {', '.join(record)} for {n_problems} problems into {traj_dir}")
    for name in record:
        policy, modes = runs[name]
        tasks = get_control_task_product(
            settings=setting, micro_protocols=policy, modes=modes, eval_config=config,
        )
        inspect_eval(tasks, **{**eval_args, "log_dir": str(traj_dir / name)})

    files = sorted(traj_dir.rglob("*.eval"))
    size_mb = sum(f.stat().st_size for f in files) / 1e6
    print(f"\nSaved {len(files)} log file(s), {size_mb:.1f} MB in total, under {traj_dir}")


# Guard needed on Windows, where worker processes re-import this file.
if __name__ == "__main__":
    main()
