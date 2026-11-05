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
5. A one-sided honest arm leaking into the analysed set. A top-up has honest samples and no
   attack samples, and `compute_safety` returns 1.0 from an empty denominator rather than
   failing, so such a file in `results/` would report perfect safety without any error.

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
    # Strip in the right order. A superseded partial is named
    # "<run>-samples.partial.csv", so replacing "-samples.csv" first matches nothing and
    # leaves a name no run can equal, which silently disabled check 4 entirely.
    def _run_name(path: Path) -> str:
        name = path.name
        for suffix in ("-samples.partial.csv", "-samples.csv", ".partial.csv", ".csv"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name

    # Two kinds live in superseded/, and they mean different things.
    #   "<run>-samples.partial.csv"  an earlier, incomplete PASS of a run that was then
    #                                repaired in place, so it legitimately shares its name
    #                                with the live run.
    #   "<run>-samples.csv"          a distinct run that a differently named run replaced,
    #                                so its name must NOT be live.
    retired_passes = {_run_name(p) for p in SUPERSEDED.glob("*.partial.csv")}
    retired = {_run_name(p) for p in SUPERSEDED.glob("*-samples.csv")}
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
        # `monitor` is deliberately NOT here: in chart-safety-at-2pct.csv it holds
        # display labels, not run names, and is checked separately below.
        for col in ("run", "other", "reference", "run_a", "run_b"):
            if col not in df.columns:
                continue
            for name in sorted(set(df[col].dropna().astype(str))):
                if name in live or name in short:
                    continue
                fail(f"{table.name}: {col}={name!r} matches no run in results/"
                     + (" (it is SUPERSEDED)" if name in (retired | retired_passes) else ""))
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
    sizeless = sorted(r for r in live if expected_size(r) is None)
    if sizeless:
        print(f"     note: {len(sizeless)} run(s) carry no size in their name, so this "
              f"check cannot gate them: {', '.join(sizeless)}")
    for run in sorted(live):
        want = expected_size(run)
        if want is None:
            continue
        summary = RESULTS / f"{run}.csv"
        if not summary.exists():
            fail(f"{run} has per-sample scores but no summary CSV")
            continue
        # Count the rows themselves. Trusting the summary's own n_honest would pass a
        # 500/500 summary sitting on top of a 943-row sample file.
        rows = pd.read_csv(RESULTS / f"{run}-samples.csv")
        got_h = int((rows["mode"] == "honest").sum())
        got_a = int((rows["mode"] == "attack").sum())
        if got_h != want or got_a != want:
            fail(f"{run} claims {want} per arm but its sample file holds {got_h} honest "
                 f"and {got_a} attack. Finish it or supersede it; do not analyse it.")
        dupes = rows.duplicated(subset=["mode", "sample_id"]).sum()
        if dupes:
            fail(f"{run} has {dupes} duplicate (mode, sample_id) rows, which double-count")
        df = pd.read_csv(summary)
        if "n_honest" in df.columns and (int(df.n_honest.iloc[0]) != got_h
                                         or int(df.n_attack.iloc[0]) != got_a):
            fail(f"{run}: summary says {int(df.n_honest.iloc[0])}/{int(df.n_attack.iloc[0])} "
                 f"but the sample file holds {got_h}/{got_a}")
    print("     done")

    print("3b. display labels in the chart feed resolve to a configured run")
    chart = ANALYSIS / "chart-safety-at-2pct.csv"
    build = Path("web/build.py")
    if chart.exists() and build.exists():
        # web/build.py maps run name -> (display label, ...). A label in the chart feed
        # that no longer appears there means the chart is carrying a configuration the
        # report can no longer explain, which is how a renamed arm goes stale unnoticed.
        import ast
        tree = ast.parse(build.read_text())
        runs_node = next((n for n in tree.body if isinstance(n, ast.Assign)
                          and getattr(n.targets[0], "id", "") == "RUNS"), None)
        if runs_node is None:
            fail("web/build.py has no RUNS mapping to check the chart feed against")
        else:
            labels = {v.elts[0].value for v in runs_node.value.values}
            for name in sorted(set(pd.read_csv(chart)["monitor"].astype(str))):
                if name not in labels:
                    fail(f"chart-safety-at-2pct.csv: monitor={name!r} is not a display "
                         f"label in web/build.py RUNS, so the chart and the report disagree")
    print("     done")

    print("4. no superseded run is also live")
    for run in sorted(retired & live):
        fail(f"{run} is live in results/ AND retired in results/superseded/ as a distinct "
             f"run, so the same name denotes two different things")
    for run in sorted(retired_passes - live):
        fail(f"{run} has a retired partial pass in results/superseded/ but no live run of "
             f"that name, so the repair it was waiting for never landed")
    if retired_passes & live:
        print(f"     note: {len(retired_passes & live)} run(s) were repaired in place, so "
              f"an earlier partial pass is retained under the same name: "
              f"{', '.join(sorted(retired_passes & live))}")
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
        source = str(df.usage_source.iloc[0])
        if source == "sample_field_complete":
            # The log carries no usage-bearing model events, so the sample-level field is
            # the only source there is. That is tolerable only because the field covers
            # every sample: Inspect empties it for a call it serves from cache, so full
            # coverage is evidence that none was cached and the total is complete. Partial
            # coverage falls through to the failure below, where it belongs.
            print(f"     note: {run} has no model events, so its usage comes from the "
                  f"sample-level field. The field covers every sample, so no call was "
                  f"cache-served and the total is complete")
        elif source != "events":
            fail(f"{run} has usage_source={source!r}; the sample-level field is blind to "
                 f"cached calls and undercounts them")
        served, total = int(df.n_cache_served.iloc[0]), int(df.n_samples.iloc[0])
        if served > 0.5 * total:
            print(f"     note: {run} was {served}/{total} cache-served, so its scores are "
                  f"inherited from an earlier pass and its billed cost is not its cost")
    print("     done")

    print("\n6. one-sided honest arms stay out of the analysed set")
    # A top-up has 500 honest samples and no attack samples. In results/ it would be read
    # as a run with an empty attack arm, and ControlArena's compute_safety returns 1.0 from
    # an empty denominator rather than failing, so it would report perfect safety in
    # silence. Three things have to hold: none is in results/, each names a live run it
    # extends, and its problems are disjoint from that run's.
    topup_dir = RESULTS / "honest-topup"
    topups = sorted(topup_dir.glob("*-samples.csv")) if topup_dir.is_dir() else []
    for name in sorted(live):
        if name.endswith("-honest-topup"):
            fail(f"{name} is a one-sided honest arm and is in results/, where every analysis "
                 f"script globs it as a run with no attack samples")
    for t in topups:
        label = t.name.replace("-samples.csv", "")
        if not label.endswith("-honest-topup"):
            fail(f"{t.name} is in honest-topup/ but is not named <run>-honest-topup")
            continue
        parent = label[: -len("-honest-topup")]
        if parent not in live:
            fail(f"{t.name} extends {parent}, which has no per-sample file in results/")
            continue
        e = pd.read_csv(t)
        if set(e["mode"].unique()) != {"honest"}:
            fail(f"{t.name} carries modes {sorted(e['mode'].unique())}; a top-up is "
                 f"honest-only by definition")
        r = pd.read_csv(RESULTS / f"{parent}-samples.csv")
        r_h = set(r[r["mode"] == "honest"].sample_id.astype(str))
        e_h = set(e.sample_id.astype(str))
        both = r_h & e_h
        if both:
            fail(f"{t.name} re-scores {len(both)} problems {parent} already has, so "
                 f"concatenating them would double-count honest rows and move every "
                 f"threshold")
        unscored = int(e.suspicion.isna().sum())
        if unscored:
            fail(f"{t.name} has {unscored} honest row(s) with no score; a missing honest "
                 f"score is a missing threshold observation, not a neutral one")
        if not both and not unscored:
            print(f"     {label}: {len(e_h)} honest samples, disjoint from {parent}'s "
                  f"{len(r_h)}, all scored")
    if not topups:
        print("     no one-sided arms present")
    print("     done")

    if "--rebuild" in sys.argv:
        print("\n7. regenerating the four generated tables and reporting drift")
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
