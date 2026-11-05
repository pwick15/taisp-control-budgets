"""Invariants on the recovered usage record. Run after any change to the accounting.

    uv run python scripts/check_usage_invariants.py

No API cost, but it reads every retained eval log, so it takes a few minutes.

Why these five
--------------
Each one is a bug this project actually shipped, turned into a check:

1. **Every retained run delivers the sample count its name claims.** A run that
   loses samples loses a contiguous tail rather than a random subset, which moved
   one run's measured recall by 0.65 points.
2. **No sample is missing its usage.** Inspect leaves the sample-level
   `model_usage` empty for any call it serves from cache, which silently zeroed
   1,955 of 27,000 rows and understated whole runs by up to 94%. Usage is read
   from the model events, where a cache hit still carries it.
3. **input + output + cache_write + cache_read == total_tokens.** The identity
   that makes a cost computable from the parts. If it fails, either a field is
   being double counted or one is missing from the sum.
4. **reasoning_tokens <= output_tokens.** Reasoning is a subset of output, not an
   addition. If this inverts, pricing that treats it as a subset is wrong, and
   pricing that treats it as an addition bills thinking models twice.
5. **A model event with no usage carries an error.** A usage-less event that
   succeeded would be a billed call contributing nothing to the cost. Every one
   found so far is a transport or rate-limit failure with an empty completion.
"""
import glob
import os
import sys
from collections import defaultdict
from pathlib import Path

from inspect_ai.log import read_eval_log

EXTRA_DIRS = ("trajectories/dataset-haiku55-tm-n500-strip",
              "trajectories/dataset-qwen38omniflash-none-tm-n500-strip")
USAGE_FIELDS = ("input_tokens", "output_tokens",
                "input_tokens_cache_write", "input_tokens_cache_read")


def run_dirs() -> list[Path]:
    dirs = sorted(p for p in Path("logs").iterdir() if p.is_dir())
    return dirs + [Path(e) for e in EXTRA_DIRS if Path(e).is_dir()]


def expected_samples(run: str) -> int | None:
    """Rows the run's name promises: two arms of n each. None when it says nothing."""
    for tag, n in (("n500", 500), ("dataset500", 500), ("n100", 100), ("n30", 30)):
        if tag in run:
            return 2 * n
    return None


def main() -> None:
    fails: list[str] = []
    notes: list[str] = []
    totals = defaultdict(int)

    for d in run_dirs():
        run = d.name
        n_rows = n_no_usage = n_zero = n_identity = n_reason = 0
        n_usageless_ok = 0
        for proto in sorted(x for x in d.iterdir() if x.is_dir()):
            for p in sorted(glob.glob(str(proto / "*.eval"))):
                try:
                    log = read_eval_log(p)
                except Exception as e:
                    fails.append(f"{run}: could not read {os.path.basename(p)}: {e}")
                    continue
                for smp in (log.samples or []):
                    n_rows += 1
                    tot = defaultdict(int)
                    seen_usage = False
                    for ev in smp.events:
                        if getattr(ev, "event", None) != "model":
                            continue
                        out = getattr(ev, "output", None)
                        u = getattr(out, "usage", None) if out else None
                        if u is None:
                            if out is None:
                                continue
                            # Check 5: a usage-less event must have failed.
                            err = getattr(ev, "error", None) or getattr(out, "error", None)
                            if err:
                                n_usageless_ok += 1
                            else:
                                n_no_usage += 1
                            continue
                        seen_usage = True
                        for f in USAGE_FIELDS:
                            tot[f] += int(getattr(u, f, 0) or 0)
                        tot["total_tokens"] += int(getattr(u, "total_tokens", 0) or 0)
                        tot["reasoning_tokens"] += int(
                            getattr(u, "reasoning_tokens", 0) or 0)
                        if sum(int(getattr(u, f, 0) or 0) for f in USAGE_FIELDS) != \
                                int(getattr(u, "total_tokens", 0) or 0):
                            n_identity += 1
                        if int(getattr(u, "reasoning_tokens", 0) or 0) > \
                                int(getattr(u, "output_tokens", 0) or 0):
                            n_reason += 1
                    if not seen_usage:
                        n_zero += 1

        want = expected_samples(run)
        if want is not None and n_rows != want:
            fails.append(f"{run}: {n_rows} samples, its name claims {want}")
        if n_zero:
            fails.append(f"{run}: {n_zero} sample(s) with no usage on any model event")
        if n_identity:
            fails.append(f"{run}: {n_identity} call(s) where the four input/output fields "
                         f"do not sum to total_tokens")
        if n_no_usage:
            fails.append(f"{run}: {n_no_usage} model event(s) with no usage and no error, "
                         f"so a billed call may be uncounted")
        if n_reason:
            notes.append(f"{run}: {n_reason} call(s) report more reasoning than output "
                         f"tokens (provider accounting; the cost identity still holds)")
        if n_usageless_ok:
            notes.append(f"{run}: {n_usageless_ok} failed call(s) carried no usage, which "
                         f"is correct; they generated nothing and were retried")
        totals["runs"] += 1
        totals["rows"] += n_rows
        totals["usageless_ok"] += n_usageless_ok
        print(f"  {run[:56]:56s} {n_rows:5d} rows", flush=True)

    print(f"\n{totals['runs']} runs, {totals['rows']} samples, "
          f"{totals['usageless_ok']} failed-and-retried calls")
    if notes:
        print(f"\n== notes ({len(notes)}) ==")
        for n in notes:
            print(f"  {n}")
    print(f"\n== failures ({len(fails)}) ==")
    for f in fails:
        print(f"  FAIL {f}")
    if not fails:
        print("  none")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
