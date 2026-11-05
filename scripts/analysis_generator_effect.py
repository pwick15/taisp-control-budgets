"""Does who wrote the backdoor matter once edit size is controlled for?

    uv run python scripts/analysis_generator_effect.py

No API cost. Reads results/analysis/case-features.csv and hard-backdoors.csv.

The question
------------
Two findings in the study look like they could be the same effect: backdoors
with small diffs are missed more often, and some generators are missed far more
often than others. If the hard generators simply write smaller diffs, there is
one finding here, not two.

Method
------
Logistic regression of `missed by every monitor` on log1p(changed_lines), with
and without generator. Two things are reported:

1. A permutation test for the generator term. Generator labels are shuffled and
   the model refit, many times, giving an empirical null for the deviance
   improvement. This avoids a chi-square approximation, which is not safe here:
   two generators have zero misses (complete separation) and several have n<25.
2. The focused o1-mini vs o3-mini contrast, adjusted for edit size, with a
   bootstrap interval on the odds ratio.

Fitting uses Newton-IRLS with a small ridge penalty, which keeps the separated
categories finite instead of diverging. The penalty biases coefficients toward
zero, so it makes the generator effect look *smaller*, not larger.
"""
import numpy as np
import pandas as pd

RIDGE = 1e-3
N_PERM = 2000
N_BOOT = 2000
SEED = 20261030


def fit_logistic(X: np.ndarray, y: np.ndarray, ridge: float = RIDGE,
                 iters: int = 100) -> tuple[np.ndarray, float]:
    """Newton-IRLS with an L2 penalty. Returns (beta, deviance)."""
    beta = np.zeros(X.shape[1])
    pen = ridge * np.eye(X.shape[1])
    pen[0, 0] = 0.0  # never penalise the intercept
    for _ in range(iters):
        eta = np.clip(X @ beta, -30, 30)
        p = 1.0 / (1.0 + np.exp(-eta))
        w = np.clip(p * (1 - p), 1e-9, None)
        z = eta + (y - p) / w
        XtW = X.T * w
        try:
            new = np.linalg.solve(XtW @ X + pen, XtW @ z)
        except np.linalg.LinAlgError:
            break
        if np.max(np.abs(new - beta)) < 1e-9:
            beta = new
            break
        beta = new
    eta = np.clip(X @ beta, -30, 30)
    p = np.clip(1.0 / (1.0 + np.exp(-eta)), 1e-12, 1 - 1e-12)
    dev = -2.0 * np.sum(y * np.log(p) + (1 - y) * np.log(1 - p))
    return beta, dev


def design(size: np.ndarray, gen: np.ndarray | None,
           levels: list[str] | None) -> np.ndarray:
    cols = [np.ones(len(size)), size]
    if gen is not None:
        for lv in levels[1:]:          # first level is the reference
            cols.append((gen == lv).astype(float))
    return np.column_stack(cols)


def main() -> None:
    rng = np.random.default_rng(SEED)
    cf = pd.read_csv("results/analysis/case-features.csv")
    hb = pd.read_csv("results/analysis/hard-backdoors.csv")
    d = cf.merge(hb[["sample_id", "n_monitors_caught@2%"]], on="sample_id")
    d["missed"] = (d["n_monitors_caught@2%"] == 0).astype(float)
    d["lsize"] = np.log1p(d["changed_lines"].to_numpy(dtype=float))

    y = d["missed"].to_numpy()
    size = d["lsize"].to_numpy()
    gen = d["model"].to_numpy()
    # Reference = the largest group, so the comparisons are against the best-measured one.
    levels = list(d["model"].value_counts().index)

    _, dev_size = fit_logistic(design(size, None, None), y)
    beta_full, dev_full = fit_logistic(design(size, gen, levels), y)
    observed = dev_size - dev_full

    print("== 1. Does generator add anything beyond edit size? ==")
    print(f"   n = {len(d)},  missed = {int(y.sum())}")
    print(f"   deviance, edit size only      : {dev_size:.2f}")
    print(f"   deviance, + generator         : {dev_full:.2f}")
    print(f"   improvement                   : {observed:.2f}  ({len(levels)-1} extra terms)")

    null = np.empty(N_PERM)
    for i in range(N_PERM):
        _, dv = fit_logistic(design(size, rng.permutation(gen), levels), y)
        null[i] = dev_size - dv
    p = (1 + int((null >= observed).sum())) / (N_PERM + 1)
    print(f"   permutation null, {N_PERM} shuffles of the generator label:")
    print(f"     median {np.median(null):.2f}, 95th pct {np.percentile(null, 95):.2f}, "
          f"max {null.max():.2f}")
    print(f"   p = {p:.4f}" + ("  -> generator carries information edit size does not"
                               if p < 0.05 else "  -> not separable from edit size"))

    print(f"\n   (edit-size coefficient in the full model: {beta_full[1]:+.3f} per log-line, "
          f"odds ratio {np.exp(beta_full[1]):.3f})")

    print("\n== 2. o1-mini vs o3-mini, adjusted for edit size ==")
    pair = d[d.model.isin(["openai/o1-mini", "openai/o3-mini"])].reset_index(drop=True)
    yp = pair["missed"].to_numpy()
    sp = pair["lsize"].to_numpy()
    is_o1 = (pair["model"] == "openai/o1-mini").to_numpy().astype(float)
    Xp = np.column_stack([np.ones(len(pair)), sp, is_o1])
    bp, _ = fit_logistic(Xp, yp)
    print(f"   n = {len(pair)}  (o1-mini {int(is_o1.sum())}, o3-mini {int(len(pair)-is_o1.sum())})")
    print(f"   unadjusted missed rate: o1-mini {yp[is_o1 == 1].mean():.1%}, "
          f"o3-mini {yp[is_o1 == 0].mean():.1%}")
    print(f"   adjusted log-odds for o1-mini: {bp[2]:+.3f}  -> odds ratio {np.exp(bp[2]):.2f}")

    boots = []
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(pair), len(pair))
        if len(np.unique(yp[idx])) < 2:
            continue
        b, _ = fit_logistic(Xp[idx], yp[idx])
        boots.append(b[2])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    print(f"   95% bootstrap interval on the odds ratio: "
          f"[{np.exp(lo):.2f}, {np.exp(hi):.2f}]  ({len(boots)} usable replicates)")
    print("   Interval excluding 1 means the generator gap survives edit-size adjustment."
          if lo > 0 else "   Interval includes 1: adjustment absorbs the gap.")


if __name__ == "__main__":
    main()
