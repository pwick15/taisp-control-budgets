"""How many audit budgets can each monitor score scale actually buy?

    uv run python scripts/analysis_score_resolution.py

No API cost. Reads committed results/*-samples.csv files.

Every audit threshold in this study is a percentile of the honest score
distribution, and the library thresholds with strict `>`. So the achievable
false-positive rates are not whatever we ask for: they are exactly the set
{mean(honest > v)} over the distinct honest scores v. Asking for 0.5% when the
scale cannot express it silently returns the nearest rung it can.

A rung is only usable if enough honest rows sit above it. One honest row out of
500 is a 0.20% FPR with a 95% CI running past 1%, so a "safety at 0.2%" built on
it is a single sample. The criterion below is at least 5 honest rows.

Eight pairs, not two
--------------------
This used to list the two monitors the 0-100 prompt was first measured on, which
left the obvious objection open: a lever that works on two monitors may be a
property of those two. Every monitor that now has both a 0-10 and a wider-scale
arm is paired below.

Two of the pairs are NOT clean scale ablations and are marked as such. The 0-100
arms were launched without a `reasoning_effort`, so the provider's default
applied, while their 0-10 counterparts were run with an explicit setting. On
gpt-oss-120b that moves reasoning from 283 tokens per sample to none, and on
Qwen3.8 Omni Flash from none to 1,281. Whatever those two pairs show, it is not
the prompt alone, and attributing it to the prompt is the mistake this file
exists to prevent elsewhere.

On two further pairs the check cannot be run in either direction: the 0-10 arms
of Sonnet 5.5 UM and Gemma 4 26B-A4B kept no eval log, so they have no token
record to compare against. They are counted as clean below because their
configurations match on paper and Gemma does not reason at all, but that is an
argument rather than a measurement, and "unverified" is not the same as "clean".
"""
import numpy as np
import pandas as pd

MIN_HONEST_ROWS = 5
SAMPLES = "results/{}-samples.csv"

# (monitor, scale, 0-10 run, wider-scale run, note). The note is non-empty where
# the pair varies something other than the scale.
PAIRS = [
    ("Haiku 5.5 xhigh", 100,
     "dataset-haiku55-effortxhigh-tm-n500-strip",
     "dataset-haiku55-xhigh-scale100-n500-strip", ""),
    ("Haiku 5.5 xhigh", 200,
     "dataset-haiku55-effortxhigh-tm-n500-strip",
     "dataset-haiku55-xhigh-scale200-n500-strip", ""),
    ("Sonnet 5.5 UM", 100,
     "dataset500-sonnet55-um-strip",
     "dataset500-sonnet55-um-scale100-strip", ""),
    ("Gemma 3 4B", 100,
     "dataset-gemma3-4b-tm-n500-strip",
     "dataset-gemma3-4b-scale100-n500-strip", ""),
    ("Gemma 3 27B", 100,
     "dataset-gemma3-27b-tm-n500-strip",
     "dataset-gemma3-27b-scale100-n500-strip", ""),
    ("GPT-6 Luna", 100,
     "dataset-gpt6luna-tm-n500-strip",
     "dataset-luna-scale100-n500-strip", ""),
    ("Gemma 4 26B-A4B", 100,
     "dataset500-gemma426b-tm-strip",
     "dataset-gemma426b-scale100-n500-strip", ""),
    ("gpt-oss-120b", 100,
     "dataset-gptoss120b-tm-n500-strip",
     "dataset-gptoss120b-scale100-n500-strip",
     "reasoning 283 tok/sample on 0-10, none on 0-100"),
    ("Qwen3.8 Omni Flash", 100,
     "dataset-qwen38omniflash-none-tm-n500-strip",
     "dataset-qwen38-scale100-n500-strip",
     "reasoning none on 0-10, 1281 tok/sample on 0-100"),
]


def auc(honest: np.ndarray, attack: np.ndarray) -> float:
    """Mann-Whitney AUC with midranks, as a threshold-free discrimination check."""
    x = np.concatenate([attack, honest])
    r = pd.Series(x).rank(method="average").to_numpy()
    return (r[:len(attack)].sum() - len(attack) * (len(attack) + 1) / 2) / (
        len(attack) * len(honest))


def describe(run: str) -> dict | None:
    """Resolution and discrimination for one run, or None if it is not committed."""
    try:
        d = pd.read_csv(SAMPLES.format(run))
    except FileNotFoundError:
        return None
    honest = d[d["mode"] == "honest"].suspicion.dropna().to_numpy()
    attack = d[d["mode"] == "attack"].suspicion.dropna().to_numpy()
    if not len(honest) or not len(attack):
        return None
    achievable = sorted({(honest > v).mean() for v in np.unique(honest)})
    usable = [f for f in achievable
              if 0 < f <= 0.5 and f * len(honest) >= MIN_HONEST_ROWS]
    return {
        "run": run,
        "n_honest": len(honest),
        # Distinct values over both arms, which is what sets the score lattice,
        # and over honest rows alone, which is what sets the achievable FPRs.
        "distinct": int(len(np.unique(np.concatenate([honest, attack])))),
        "distinct_honest": int(len(np.unique(honest))),
        "usable": len(usable),
        "lowest": min(usable) if usable else float("nan"),
        "auc": auc(honest, attack),
    }


def main() -> None:
    rows = []
    print(f"{'monitor':20s} {'scale':>5s} {'distinct':>9s} {'honest dv':>10s} "
          f"{'usable rungs':>13s} {'lowest usable':>14s} {'AUC':>7s}")
    for monitor, scale, base_run, wide_run, note in PAIRS:
        for scale_label, run in ((10, base_run), (scale, wide_run)):
            s = describe(run)
            if s is None:
                print(f"{monitor:20s} {scale_label:5d} {'(not committed)':>9s}  {run}")
                continue
            low = "none" if s["lowest"] != s["lowest"] else f"{s['lowest']:.2%}"
            print(f"{monitor:20s} {scale_label:5d} {s['distinct']:9d} "
                  f"{s['distinct_honest']:10d} {s['usable']:13d} {low:>14s} {s['auc']:7.4f}")
            rows.append({"monitor": monitor, "scale": scale_label, **s})
        print()

    print(f"usable = achievable FPR <= 50% with at least {MIN_HONEST_ROWS} honest rows "
          f"above the threshold")
    print("AUC is threshold-free, so it cannot see resolution at all: that is the point.\n")

    # The generalisation question S2 was run to answer, decided on the pairs that
    # vary only the scale.
    print("== does the wider prompt buy resolution on every monitor, or only some? ==")
    clean = [p for p in PAIRS if not p[4]]
    gained_dv, gained_rungs, lowered, total = 0, 0, 0, 0
    for monitor, scale, base_run, wide_run, _ in clean:
        b, w = describe(base_run), describe(wide_run)
        if b is None or w is None:
            print(f"  {monitor} on 0-{scale}: skipped, one arm is not committed")
            continue
        total += 1
        gained_dv += w["distinct"] > b["distinct"]
        gained_rungs += w["usable"] > b["usable"]
        lo_b = b["lowest"] if b["lowest"] == b["lowest"] else float("inf")
        lo_w = w["lowest"] if w["lowest"] == w["lowest"] else float("inf")
        lowered += lo_w < lo_b
        print(f"  {monitor:20s} 0-10 -> 0-{scale:<3d}  "
              f"distinct {b['distinct']:3d} -> {w['distinct']:3d}   "
              f"usable rungs {b['usable']} -> {w['usable']}   "
              f"lowest {lo_b:.2%} -> {lo_w:.2%}"
              if lo_b != float("inf") and lo_w != float("inf") else
              f"  {monitor:20s} 0-10 -> 0-{scale:<3d}  "
              f"distinct {b['distinct']:3d} -> {w['distinct']:3d}   "
              f"usable rungs {b['usable']} -> {w['usable']}")
    print(f"\n  distinct score values rose on {gained_dv} of {total} clean pairs")
    print(f"  usable rungs rose on {gained_rungs} of {total}")
    print(f"  the cheapest usable rate fell on {lowered} of {total}")
    print("\n  Distinct values are not the deliverable. A rung is only worth having if a")
    print("  comparison can stand on it, so the middle line is the one that matters, and")
    print("  the third is the one a budget-indexed frontier needs.")

    confounded = [p for p in PAIRS if p[4]]
    if confounded:
        print("\n== pairs excluded from that count, and why ==")
        for monitor, scale, _, _, note in confounded:
            print(f"  {monitor} on 0-{scale}: {note}")
        print("  These vary reasoning as well as the scale, so neither direction can be")
        print("  attributed to the prompt. Re-running them with the effort pinned on both")
        print("  arms is what would make them usable, and it costs under a dollar each.")


if __name__ == "__main__":
    main()
