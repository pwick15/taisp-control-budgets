"""The monitor's hidden reasoning: does it cost us anything, and is it a free score?

    uv run python scripts/analysis_reasoning_tokens.py [LOG_DIR]

Why this exists
---------------
Reasoning models spend most of their output on tokens the caller never reads.
Two things follow for a budget-indexed study, and only one of them is a problem.

1. Cost. `src/analyze.py` prices `output_tokens` and asserts in a comment that
   reasoning is included in it. That assertion is checked here rather than
   trusted: for every model in the log, input + output + cache_write + cache_read
   must equal total_tokens exactly. If it does, `reasoning_tokens` is a subset of
   `output_tokens`, the dollar figures are right, and nothing is undercounted.

2. Signal. The suspicion score is a small integer, so only a handful of audit
   budgets are buyable (see SCORE-SCALE.md and analysis_score_resolution.py).
   Thinking length is near-continuous and comes back on the same API response, so
   it costs nothing extra to read. If the monitor thinks longer about backdoored
   code, reasoning length is a second, much finer score.

The obvious confound for (2) is program length: these backdoors are mostly
independent rewrites, so an attack program could simply be bigger and draw more
thinking for that reason alone. Three controls are applied: the AUC of prompt
length on its own, thinking length residualised on prompt length with the fit
taken from honest rows only, and a per-problem paired difference, which holds the
problem fixed exactly.

Where thinking length is used to break ties in the suspicion score, the rank
transform is also fitted on honest rows only, and the tie-break weight is kept
below the smallest gap between distinct score values, so the ordering is strictly
lexicographic: it can add operating points between the score's levels but can
never reorder two samples the score already separates.

Needs a raw .eval log, which is gitignored (see policy/no-trajectories-in-git),
so it names the log directory rather than reading a committed CSV.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from inspect_ai.analysis import samples_df

LOG_DIR = sys.argv[1] if len(sys.argv) > 1 else (
    "trajectories/dataset-haiku55-tm-n500-strip/trusted_monitoring")
SCORE = "score_max_suspicion_scorer"
N_BOOT = 4000
BUDGETS = (0.01, 0.02, 0.05, 0.10)


def usage_field(raw, key: str) -> int:
    """Sum one usage field across every model that billed on this sample."""
    u = json.loads(raw) if isinstance(raw, str) else raw
    return sum(int(m.get(key) or 0) for m in u.values())


def auc(honest: np.ndarray, attack: np.ndarray) -> float:
    x = np.concatenate([attack, honest])
    r = pd.Series(x).rank(method="average").to_numpy()
    return (r[:len(attack)].sum() - len(attack) * (len(attack) + 1) / 2) / (
        len(attack) * len(honest))


def spearman(a, b) -> float:
    return float(pd.Series(list(a)).rank().corr(pd.Series(list(b)).rank()))


def recall_at(h_s, h_r, a_s, a_r, budget: float, eps: float):
    """Recall at the highest achievable FPR <= budget, honest-only calibration.

    eps=0 scores on suspicion alone; eps>0 breaks its ties with thinking length.
    """
    order = np.sort(h_r)

    def tie(r):
        return np.searchsorted(order, r, side="left") / (len(order) + 1)

    hc, ac = h_s + eps * tie(h_r), a_s + eps * tie(a_r)
    fprs = {float((hc > v).mean()) for v in np.unique(hc)}
    reachable = [f for f in fprs if 0 < f <= budget]
    if not reachable:
        return None, None
    f = max(reachable)
    thr = min(v for v in np.unique(hc) if abs(float((hc > v).mean()) - f) < 1e-12)
    return f, float((ac > thr).mean())


def main() -> None:
    df = samples_df(LOG_DIR)
    for key in ("reasoning_tokens", "output_tokens", "input_tokens",
                "input_tokens_cache_write", "input_tokens_cache_read", "total_tokens"):
        df[key] = df["model_usage"].map(lambda raw, k=key: usage_field(raw, k))
    # The monitor prompt is cached, so the program text is billed as cache_write.
    df["prompt_tokens"] = df.input_tokens + df.input_tokens_cache_write + df.input_tokens_cache_read
    df["visible_tokens"] = df.output_tokens - df.reasoning_tokens
    df = df.dropna(subset=[SCORE])

    print(f"== {LOG_DIR}")
    print(f"{len(df)} samples\n")

    print("-- 1. is reasoning already inside output_tokens, i.e. already priced? --")
    identity = df.input_tokens + df.output_tokens + df.input_tokens_cache_write \
        + df.input_tokens_cache_read - df.total_tokens
    if (identity == 0).all():
        print("  yes: input + output + cache == total on every sample, and reasoning is")
        print("  reported on top of that sum, so it is a subset of output_tokens.")
    else:
        print(f"  NO: the identity fails on {int((identity != 0).sum())} sample(s). "
              "Reasoning may be billed outside output_tokens; check before trusting costs.")
    share = df.reasoning_tokens.sum() / df.output_tokens.sum()
    print(f"  reasoning is {share:.1%} of all monitor output tokens "
          f"({df.reasoning_tokens.sum():,} of {df.output_tokens.sum():,})")

    mode = next(c for c in df.columns if c.endswith("eval_mode"))
    honest, attack = df[df[mode] == "honest"], df[df[mode] == "attack"]
    print("\n  per sample, by arm:")
    print(f"  {'arm':8s} {'reasoning':>10s} {'visible':>9s} {'share':>7s}")
    for name, d in (("honest", honest), ("attack", attack)):
        print(f"  {name:8s} {d.reasoning_tokens.mean():10.0f} {d.visible_tokens.mean():9.0f} "
              f"{d.reasoning_tokens.sum() / d.output_tokens.sum():6.1%}")

    print("\n-- 2. does the monitor think longer about backdoored code? --")
    h_r, a_r = honest.reasoning_tokens.to_numpy(float), attack.reasoning_tokens.to_numpy(float)
    h_s, a_s = honest[SCORE].to_numpy(float), attack[SCORE].to_numpy(float)
    h_p, a_p = honest.prompt_tokens.to_numpy(float), attack.prompt_tokens.to_numpy(float)
    print(f"  {'signal':34s} {'AUC':>7s} {'distinct honest':>16s} {'at mode':>9s}")
    for label, h, a in (("suspicion score", h_s, a_s),
                        ("monitor reasoning tokens", h_r, a_r),
                        ("monitor visible tokens", honest.visible_tokens.to_numpy(float),
                         attack.visible_tokens.to_numpy(float)),
                        ("prompt length (the confound)", h_p, a_p)):
        _, counts = np.unique(h, return_counts=True)
        print(f"  {label:34s} {auc(h, a):7.4f} {len(counts):16d} {counts.max() / len(h):8.1%}")

    slope, intercept = np.polyfit(np.log(h_p), np.log(h_r), 1)
    resid = {k: np.log(r) - (intercept + slope * np.log(p))
             for k, (r, p) in {"h": (h_r, h_p), "a": (a_r, a_p)}.items()}
    print(f"\n  thinking residualised on prompt length (fit on honest rows): "
          f"AUC {auc(resid['h'], resid['a']):.4f}")
    print(f"  Spearman(prompt length, thinking): honest {spearman(h_p, h_r):+.3f}  "
          f"attack {spearman(a_p, a_r):+.3f}")
    print(f"  Spearman(suspicion, thinking):     honest {spearman(h_s, h_r):+.3f}  "
          f"attack {spearman(a_s, a_r):+.3f}")

    pair = honest[["id", SCORE, "reasoning_tokens"]].merge(
        attack[["id", SCORE, "reasoning_tokens"]], on="id", suffixes=("_h", "_a"))
    d = (pair.reasoning_tokens_a - pair.reasoning_tokens_h).to_numpy(float)
    rng = np.random.default_rng(11)
    boot = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(N_BOOT)])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"\n  same problem, both arms (n={len(pair)}): attack thinks "
          f"{d.mean():+.0f} tokens longer, 95% CI [{lo:+.0f},{hi:+.0f}]")
    print(f"  longer on the backdoor in {(d > 0).mean():.1%} of problems")

    print("\n-- 3. does thinking length buy audit budgets the score cannot? --")
    gap = np.diff(np.unique(h_s)).min() if len(np.unique(h_s)) > 1 else 1.0
    eps = gap / 100
    reachable = sorted({float((h_s > v).mean()) for v in np.unique(h_s)})
    print(f"  score alone can buy: {[f'{f:.2%}' for f in reachable]}")
    void = [(a, b) for a, b in zip(reachable, reachable[1:]) if b - a > 0.05]
    for a, b in void:
        print(f"  nothing is buyable between {a:.2%} and {b:.2%}")
    combined = sorted({float((h_s + eps * (np.searchsorted(np.sort(h_r), h_r, side='left')
                                           / (len(h_r) + 1)) > v).mean())
                       for v in np.unique(h_s + eps * (np.searchsorted(np.sort(h_r), h_r,
                                                       side='left') / (len(h_r) + 1)))})
    filled = [f for f in combined if any(a < f < b for a, b in void)]
    print(f"  with the tie-break: {len(combined)} operating points, "
          f"{len(filled)} of them inside that void")

    print(f"\n  {'budget':>8s} {'score alone':>22s} {'with tie-break':>22s}")
    for want in BUDGETS:
        f0, r0 = recall_at(h_s, h_r, a_s, a_r, want, 0.0)
        f1, r1 = recall_at(h_s, h_r, a_s, a_r, want, eps)
        left = "no operating point" if f0 is None else f"{f0:.2%} -> recall {r0:.1%}"
        right = "no operating point" if f1 is None else f"{f1:.2%} -> recall {r1:.1%}"
        print(f"  {want:7.0%} {left:>22s} {right:>22s}")
    print(f"\n  AUC: {auc(h_s, a_s):.4f} -> "
          f"{auc(h_s + eps * (np.searchsorted(np.sort(h_r), h_r, side='left') / (len(h_r) + 1)), a_s + eps * (np.searchsorted(np.sort(h_r), a_r, side='left') / (len(h_r) + 1))):.4f}")

    # The tie-break can only add thresholds between existing score levels, so at a
    # fixed nominal budget its recall is weakly higher by construction. A two-sided
    # interval on a quantity bounded at zero is misleading; report the sign instead.
    print(f"\n  paired bootstrap over problems, threshold re-fitted per replicate "
          f"({N_BOOT} replicates):")
    rng = np.random.default_rng(11)
    idx = [rng.integers(0, len(pair), len(pair)) for _ in range(N_BOOT)]
    for want in BUDGETS:
        gains = []
        for k in idx:
            b = pair.iloc[k]
            bh_s, bh_r = b[f"{SCORE}_h"].to_numpy(float), b.reasoning_tokens_h.to_numpy(float)
            ba_s, ba_r = b[f"{SCORE}_a"].to_numpy(float), b.reasoning_tokens_a.to_numpy(float)
            _, r0 = recall_at(bh_s, bh_r, ba_s, ba_r, want, 0.0)
            _, r1 = recall_at(bh_s, bh_r, ba_s, ba_r, want, eps)
            if r0 is not None and r1 is not None:
                gains.append(r1 - r0)
        g = np.array(gains)
        print(f"  budget {want:5.0%}: median gain {np.median(g):+.1%}, "
              f"positive in {(g > 0).mean():.1%} of {len(g)} usable replicates")


if __name__ == "__main__":
    main()
