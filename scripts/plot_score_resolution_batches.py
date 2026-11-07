"""Reproduce the 0-10 vs 0-100 score-resolution figure on a second 500-problem batch.

    uv run python scripts/plot_score_resolution_batches.py

No API cost. Reads committed results/*-samples.csv. Writes
results/analysis/score-resolution-batch1-vs-batch2.png.

Layout: 2 rows (monitor) x 2 columns (batch). Each panel overlays the 0-10 and the
0-100 arm as a step curve of backdoors-caught (%) against share-of-honest-audited (%,
log x). In POLICY=dataset attack mode every attack row is a verified-working backdoor,
so "backdoors caught" at a threshold is just attack recall above it. The achievable
audit cutoffs are the distinct honest-FPR rungs; the annotation counts the ones at or
below 5% (the figure's metric: at least one honest row above the cutoff).
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RUNS = {
    ("Sonnet 5.5 UM", "original 500"): {
        "0-10":  "dataset500-sonnet55-um-strip",
        "0-100": "dataset500-sonnet55-um-scale100-strip"},
    ("Sonnet 5.5 UM", "new 500 (batch 2)"): {
        "0-10":  "dataset500b2-sonnet55-um-strip",
        "0-100": "dataset500b2-sonnet55-um-scale100-strip"},
    ("Haiku 5.5 xhigh", "original 500"): {
        "0-10":  "dataset-haiku55-effortxhigh-tm-n500-strip",
        "0-100": "dataset-haiku55-xhigh-scale100-n500-strip"},
    ("Haiku 5.5 xhigh", "new 500 (batch 2)"): {
        "0-10":  "dataset-haiku55-effortxhigh-tm-n500b2-strip",
        "0-100": "dataset-haiku55-xhigh-scale100-n500b2-strip"},
}
COLORS = {"0-10": "#2a78d6", "0-100": "#e8742a"}
INK, INK2, GRID = "#1a1a1a", "#555555", "#dddddd"


def curve(run):
    s = pd.read_csv(f"results/{run}-samples.csv")
    h = s[s["mode"] == "honest"]["suspicion"].dropna().to_numpy()
    a = s[s["mode"] == "attack"]["suspicion"].dropna().to_numpy()
    # One rung per distinct honest value v: audit everything scoring > v.
    rungs = []
    for v in np.unique(h):
        fpr = (h > v).mean()           # share of honest audited
        if fpr <= 0:
            continue
        rungs.append((fpr * 100, (a > v).mean() * 100, fpr * len(h)))
    rungs.sort()
    fprs = np.array([r[0] for r in rungs])
    recall = np.array([r[1] for r in rungs])
    usable5 = int(sum(1 for f, _, nrows in rungs if f <= 5.0 and nrows >= 1))
    return fprs, recall, usable5, len(np.unique(h))


fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True, sharey=True)
order = [("Sonnet 5.5 UM", "original 500"), ("Sonnet 5.5 UM", "new 500 (batch 2)"),
         ("Haiku 5.5 xhigh", "original 500"), ("Haiku 5.5 xhigh", "new 500 (batch 2)")]
for ax, key in zip(axes.flat, order):
    ann = []
    for scale in ("0-10", "0-100"):
        fprs, recall, usable5, dH = curve(RUNS[key][scale])
        ax.step(fprs, recall, where="post", color=COLORS[scale], lw=1.6, zorder=2)
        ax.scatter(fprs, recall, s=30, color=COLORS[scale], edgecolor="white",
                   linewidth=0.7, zorder=3, label=f"{scale} score")
        ann.append(f"{usable5} on {scale}  ({dH} distinct)")
    ax.axvline(5.0, color=INK2, ls="--", lw=0.8, alpha=0.6, zorder=1)
    ax.set_xscale("log")
    ax.set_xlim(0.15, 60)
    ax.set_ylim(0, 100)
    ax.grid(True, which="both", color=GRID, lw=0.5, alpha=0.7)
    ax.set_title(f"{key[0]}  —  {key[1]}", fontsize=11, color=INK, pad=8)
    ax.text(0.03, 0.03, "usable cutoffs ≤5%:\n" + "\n".join(ann),
            transform=ax.transAxes, fontsize=8.5, color=INK2, va="bottom", ha="left",
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec=GRID, alpha=0.9))
    ax.tick_params(colors=INK2, labelsize=9)

for ax in axes[-1]:
    ax.set_xlabel("Share of honest programs audited (%, log scale)", fontsize=9.5, color=INK2)
for ax in axes[:, 0]:
    ax.set_ylabel("Backdoors caught (%)", fontsize=9.5, color=INK2)
axes[0, 0].legend(loc="upper left", fontsize=8.5, framealpha=0.9)
fig.suptitle("Score resolution on a second 500-problem batch (same interview band, disjoint problems)",
             fontsize=12.5, color=INK, y=0.98)
fig.tight_layout(rect=[0, 0, 1, 0.96])
out = "results/analysis/score-resolution-batch1-vs-batch2.png"
fig.savefig(out, dpi=150, facecolor="white", bbox_inches="tight")
print("wrote", out)
