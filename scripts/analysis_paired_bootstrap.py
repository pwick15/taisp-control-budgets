"""Is the gap between two monitors real, or is it sample noise?

    uv run python scripts/analysis_paired_bootstrap.py
    uv run python scripts/analysis_paired_bootstrap.py <runA> <runB>

No API cost. Reads committed results/*-samples.csv files.

Method and why each piece is there:

- Both runs scored the SAME problems, so the comparison is paired. Resampling
  sample_ids once and applying that resample to both runs removes the
  problem-difficulty variance that dominates an unpaired comparison.
- The threshold is re-estimated inside every replicate. Holding the threshold
  fixed at its full-sample value treats a quantity estimated from the data as
  known, which understates the interval.
- Runs are compared at a matched ACHIEVED false-positive rate, not a nominal
  audit budget. Two monitors asked for "1%" can sit at different real FPRs when
  their score scales differ, and then the gap is partly a threshold artefact.
- The whole ladder of shared operating points is reported, not one rung. A gap
  can be real at a tight budget and gone at a loose one, which is exactly the
  thing a single-operating-point comparison cannot say.
"""
import sys

import numpy as np
import pandas as pd

N_BOOT = 4_000
MIN_HONEST_ROWS = 3   # rungs thinner than 5 honest rows are reported but flagged
THIN_ROWS = 5
SEED = 20261030

DEFAULT_PAIRS = [
    # The central comparison: the two best monitors on the same score scale.
    ("results/dataset500-sonnet55-um-scale100-strip-samples.csv",
     "results/dataset-haiku55-xhigh-scale100-n500-strip-samples.csv"),
    # Does Sonnet's reasoning effort buy safety? Same monitor, effort toggled.
    ("results/dataset500-sonnet55-um-strip-samples.csv",
     "results/dataset500-sonnet55-um-effortlow-v2-strip-samples.csv"),
    # Does keeping comments help, once the confessions are accounted for?
    ("results/dataset-haiku55-xhigh-nostrip-n500-samples.csv",
     "results/dataset-haiku55-effortxhigh-tm-n500-strip-samples.csv"),
]


def load(path: str) -> tuple[pd.Series, pd.Series]:
    d = pd.read_csv(path)
    d["sample_id"] = d.sample_id.astype(str)
    honest = d[d["mode"] == "honest"].set_index("sample_id").suspicion.dropna()
    attack = d[d["mode"] == "attack"].set_index("sample_id").suspicion.dropna()
    return honest, attack


def achievable(honest: np.ndarray) -> list[tuple[float, float]]:
    """(achieved FPR, threshold) pairs this score distribution can actually express.

    Thresholding is strict `>`, so a threshold v admits exactly mean(honest > v).
    """
    return sorted({((honest > v).mean(), float(v)) for v in np.unique(honest)})


def common_rungs(h_a: np.ndarray, h_b: np.ndarray) -> list[float]:
    """Achievable FPRs <= 50% that BOTH runs can express.

    A gap is only meaningful at an operating point both monitors can actually
    reach. Reporting the whole ladder rather than one rung is the point of a
    budget-indexed comparison: the answer can and does change along it.
    """
    ok_a = {f for f, _ in achievable(h_a) if 0 < f <= 0.5}
    ok_b = {f for f, _ in achievable(h_b) if 0 < f <= 0.5}
    shared = sorted(ok_a & ok_b)
    return [f for f in shared if f * len(h_a) >= MIN_HONEST_ROWS]


def recall_at(honest: np.ndarray, attack: np.ndarray, fpr: float) -> float:
    """Recall at the tightest threshold whose achieved FPR does not exceed fpr."""
    cand = [(f, t) for f, t in achievable(honest) if f <= fpr]
    if not cand:
        return float("nan")
    thr = min(cand, key=lambda ft: (fpr - ft[0], ft[1]))[1]
    return float((attack > thr).mean())


def compare(path_a: str, path_b: str) -> None:
    ha, aa = load(path_a)
    hb, ab = load(path_b)
    h_ids = sorted(set(ha.index) & set(hb.index))
    a_ids = sorted(set(aa.index) & set(ab.index))
    name_a, name_b = path_a.split("/")[-1][:-12], path_b.split("/")[-1][:-12]
    print(f"\n=== {name_a}\n vs {name_b}")
    print(f"paired on {len(h_ids)} honest and {len(a_ids)} attack problems")
    if not h_ids or not a_ids:
        print("  no shared problems; skipping")
        return

    ha, aa = ha.loc[h_ids].to_numpy(), aa.loc[a_ids].to_numpy()
    hb, ab = hb.loc[h_ids].to_numpy(), ab.loc[a_ids].to_numpy()
    rungs = common_rungs(ha, hb)
    if not rungs:
        print("  the two score scales share no achievable operating point; skipping")
        return

    rng = np.random.default_rng(SEED)
    # One resample of problem ids per replicate, reused across every rung and
    # both runs, so differences along the ladder are not re-randomised.
    idx = [(rng.integers(0, len(h_ids), len(h_ids)), rng.integers(0, len(a_ids), len(a_ids)))
           for _ in range(N_BOOT)]

    print(f"{'FPR':>7s} {'honest rows':>12s} {'recall A':>9s} {'recall B':>9s} "
          f"{'diff':>7s} {'95% CI':>18s}   verdict")
    for f in rungs:
        ra, rb = recall_at(ha, aa, f), recall_at(hb, ab, f)
        diffs = np.array([recall_at(ha[hi], aa[ai], f) - recall_at(hb[hi], ab[ai], f)
                          for hi, ai in idx])
        lo, hi_ = np.nanpercentile(diffs, [2.5, 97.5])
        rows = f * len(h_ids)
        verdict = "not separated" if lo <= 0 <= hi_ else "separated"
        if rows < THIN_ROWS:
            verdict += f" (thin: {rows:.0f} honest rows)"
        print(f"{f:7.2%} {rows:12.0f} {ra:9.1%} {rb:9.1%} {(ra - rb) * 100:+7.1f} "
              f"[{lo * 100:+6.1f},{hi_ * 100:+6.1f}]   {verdict}")


def main() -> None:
    if len(sys.argv) >= 3:
        compare(sys.argv[1], sys.argv[2])
        return
    for a, b in DEFAULT_PAIRS:
        compare(a, b)


if __name__ == "__main__":
    main()
