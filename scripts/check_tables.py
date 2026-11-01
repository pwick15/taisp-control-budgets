"""Fail on the data-record defects that actually bit this project.

    uv run python scripts/check_tables.py              # the fast referential checks
    uv run python scripts/check_tables.py --rebuild     # also regenerate and report drift

There is no CI in this repo, so this is a script to run by hand before publishing a number
or merging a branch. It targets the four failure modes that reached committed results, each
of which was found by hand and would have been caught here:

1. A stale run name in a committed table. A run was renamed and four tables kept the old
   name in 21 rows. Two consumers join on that column and drop an unmatched row silently,
   which removed a bar from the report chart without any error.
2. A run missing from a table it belongs in, for the same reason in reverse.
3. An incomplete run treated as a complete one. A run labelled n500 that returns 480 and 463
   is not a smaller run, it is a broken one, and its losses are not a random subset.
4. A superseded run leaking back into the analysed set, which would double-count rows that a
   repair pass already replaced.

The --rebuild pass regenerates the four generated tables and reports any cell that moved.
That is meaningful because the bootstrap seeds per run from a CRC of the run name, so the
intervals are reproducible rather than merely stable in distribution.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd

RESULTS = Path("results")
ANALYSIS = RESULTS / "analysis"
SUPERSEDED = RESULTS / "superseded"
GENERATED = ["analysis_ci.py", "analysis_achieved_fpr.py", "analysis_matched_fpr.py",
             "chart_data_2pct.py"]
problems: list[str] = []


def fail(msg: str) -> None:
    problems.append(msg)
    print(f"  FAIL  {msg}")


def expected_size(run: str) -> int | None:
    if "n500" in run or run.startswith("dataset500"):
        return 500
    if "n100" in run:
        return 100
    if "n30" in run:
        return 30
    return None


def main() -> int:
    live = {p.name.replace("-samples.csv", "")
            for p in RESULTS.glob("*-samples.csv")}
    retired = {p.name.replace("-samples.csv", "").replace(".partial", "")
               for p in SUPERSEDED.glob("*-samples*.csv")}
    print(f"{len(live)} runs with per-sample scores, {len(retired)} superseded\n")

    print("1. run names referenced by committed tables exist")
    # Different tables shorten the same run name differently: some drop only the
    # "dataset-" prefix, others also drop the "-tm-n500-strip" tail, so
    # dataset-haiku55-tm-n500-strip appears as both "haiku55-tm-n500-strip" and "haiku55".
    # Build every prefix/suffix combination rather than one aggressive strip, or the check
    # reports its own normalisation as a defect.
    PREFIXES = ("", "dataset500-", "dataset-")
    SUFFIXES = ("", "-tm-n500-strip", "-n500-strip", "-tm-strip", "-tm-n500", "-n500",
                "-strip")
    short: dict[str, str] = {}
    for run in live:
        for pre in PREFIXES:
            base = run.removeprefix(pre) if pre else run
            for suf in SUFFIXES:
                form = base.removesuffix(suf) if suf else base
                if form:
                    short.setdefault(form, run)
    for table in sorted(ANALYSIS.glob("*.csv")):
        df = pd.read_csv(table)
        for col in ("run", "other"):
            if col not in df.columns:
                continue
            for name in sorted(set(df[col].dropna().astype(str))):
                if name in live or name in short:
                    continue
                fail(f"{table.name}: {col}={name!r} matches no run in results/"
                     + (" (it is SUPERSEDED)" if name in retired else ""))
    print("     done")

    print("2. complete runs appear in the tables that index every run")
    for table in ("safety-with-ci.csv", "achieved-fpr.csv"):
        path = ANALYSIS / table
        if not path.exists():
            fail(f"{table} is missing")
            continue
        listed = set(pd.read_csv(path)["run"].astype(str))
        for run in sorted(live):
            if expected_size(run) == 500 and run not in listed:
                fail(f"{table}: complete run {run} is absent, so anything joining on "
                     f"`run` drops it silently")
    print("     done")

    print("3. every run delivers the sample count its name claims")
    for run in sorted(live):
        want = expected_size(run)
        if want is None:
            continue
        summary = RESULTS / f"{run}.csv"
        if not summary.exists():
            fail(f"{run} has per-sample scores but no summary CSV")
            continue
        df = pd.read_csv(summary)
        if "n_honest" not in df.columns:
            continue
        got_h, got_a = int(df.n_honest.iloc[0]), int(df.n_attack.iloc[0])
        if got_h != want or got_a != want:
            fail(f"{run} claims {want} per arm but delivers {got_h} honest and "
                 f"{got_a} attack. Finish it or supersede it; do not analyse it.")
    print("     done")

    print("4. no superseded run is also live")
    for run in sorted(retired & live):
        fail(f"{run} exists in BOTH results/ and results/superseded/")
    print("     done")

    print("5. cost and token figures carry their provenance")
    for run in sorted(live):
        summary = RESULTS / f"{run}.csv"
        if not summary.exists():
            continue
        df = pd.read_csv(summary)
        if "usage_source" not in df.columns:
            print(f"     note: {run} predates the provenance columns, so its cost cannot "
                  f"be told apart from a cache-served one")
            continue
        if str(df.usage_source.iloc[0]) != "events":
            fail(f"{run} has usage_source={df.usage_source.iloc[0]!r}; the sample-level "
                 f"field is blind to cached calls and undercounts them")
        served, total = int(df.n_cache_served.iloc[0]), int(df.n_samples.iloc[0])
        if served > 0.5 * total:
            print(f"     note: {run} was {served}/{total} cache-served, so its scores are "
                  f"inherited from an earlier pass and its billed cost is not its cost")
    print("     done")

    if "--rebuild" in sys.argv:
        print("\n6. regenerating the four generated tables and reporting drift")
        env = dict(os.environ)
        for script in GENERATED:
            subprocess.run([sys.executable, f"scripts/{script}"], check=False,
                           capture_output=True, env=env)
        drift = subprocess.run(["git", "diff", "--stat", "--", str(ANALYSIS)],
                               capture_output=True, text=True).stdout.strip()
        if drift:
            fail("a regenerated table does not match the committed one:\n" + drift)
        else:
            print("     every regenerated cell matches the committed table")

    print(f"\n{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
