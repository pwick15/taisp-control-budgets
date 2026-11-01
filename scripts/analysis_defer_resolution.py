"""Does the resolution pathology reappear on the deferral axis? Yes, worse.

    uv run python scripts/analysis_defer_resolution.py

No API cost. Reads the committed defer-to-trusted sweep.

Why this exists
---------------
The study's central methodological finding is that a requested audit budget is
not an achievable one: thresholds are percentiles of a handful of distinct
honest scores, applied with strict `>`, so asking for 0.5% silently returns
whatever rung the scale can express. Defer-to-trusted adds a second threshold of
exactly the same construction, over the same honest scores. If the diagnosis is
right, the defer axis should collapse the same way, and a defer sweep should
realise far fewer settings than it nominally requests.

It does, and by more than the audit axis does.

Why this reads a committed CSV rather than re-running the simulator
-------------------------------------------------------------------
`src/defer_sim.py` replays deferral offline for any (audit, defer) pair at zero
API cost, which is what makes this cheap to extend. It cannot be re-run here:
it needs the monitored eval logs, and the n=100 defer configuration's logs were
not retained. `results/sonnet55-n100-haiku45-strip-dtt.csv` is the only record
of that sweep, so this quantifies what that file already contains instead of
generating more of it. Extending the sweep needs the monitor re-run on those
100 problems first, which is the same log-retention gap that leaves five n=500
runs without a cost.
"""
from pathlib import Path

import pandas as pd

CSV = Path("results/sonnet55-n100-haiku45-strip-dtt.csv")


def main() -> None:
    d = pd.read_csv(CSV)
    # float() on each, because a numpy scalar prints as np.float64(0.0) inside a list
    # and these lines are read by people.
    nominal = sorted(float(x) for x in d.defer_pct.unique())
    realised = sorted(float(x) for x in d.honest_deferred_frac.unique())
    thresholds = sorted(d.defer_threshold.astype(str).unique())

    print(f"{CSV}: {len(d)} rows, "
          f"{d.audit_budget_pct.nunique()} audit budgets x {len(nominal)} defer settings\n")
    print(f"nominal defer settings requested : {len(nominal)}  {nominal}")
    print(f"deferral fractions realised      : {len(realised)}  {realised}")
    print(f"distinct defer thresholds        : {len(thresholds)}  {thresholds}")
    print(f"\nSo {len(nominal)} requests buy {len(realised)} operating points. The threshold is a")
    print("percentile of the same concentrated honest distribution the audit cutoff uses, so")
    print("the defer knob has the same lattice and most of its settings are aliases.\n")

    print("== per audit budget, how many distinct (defer, safety, usefulness) points ==")
    for b, g in d.groupby("audit_budget_pct"):
        pts = g[["honest_deferred_frac", "safety", "usefulness"]].drop_duplicates()
        print(f"  budget {b:5.1f}%   {len(pts)} distinct of {len(g)} requested")

    u_alone = float(d.usefulness_u_alone.iloc[0])
    t_alone = float(d.usefulness_t_alone.iloc[0])
    us = sorted(float(x) for x in d.usefulness.unique())
    print(f"\n== the usefulness axis ==")
    print(f"  U alone {u_alone:.2f}, T alone {t_alone:.2f}, so the whole range is "
          f"{100 * (u_alone - t_alone):.0f} points")
    print(f"  values the sweep actually reaches: {us}")
    print(f"  that is {len(us)} points across a {100 * (u_alone - t_alone):.0f}-point range, "
          f"and two of them are the endpoints")
    print("\n  The endpoints are not measurements. defer=0 is plain trusted monitoring and")
    print("  defer=100% is T alone, so the sweep buys exactly "
          f"{len(us) - 2} interior points on the")
    print("  usefulness axis. A tradeoff curve cannot be drawn through that.")

    print("\n== what this means for the study ==")
    print("  The deferral axis is not a second dimension the study can report. It is the")
    print("  audit axis again, read through the same lattice, and at n=100 it is coarser")
    print("  still. Reporting a defer-to-trusted frontier here would be reporting the")
    print("  interpolation between two endpoints as though it were data.")


if __name__ == "__main__":
    main()
