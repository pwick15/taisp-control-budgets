"""Read the Opus 5.5 runs on the 51 hard backdoors: spend, parse failures, and the per-sample chart. No API cost.

    uv run python scripts/analysis_opus_hard51.py                 # every logs/hard51-opus55-effort* run found
    LOG_GLOB='/tmp/x/hard51-opus55-effort*' uv run python scripts/analysis_opus_hard51.py   # other location
    BUDGET=7.00 RESERVE=0.50 ...                                   # for the "can I afford the next level" line

Each run is one reasoning effort over the same 51 backdoored samples (scripts/build_hard51.py), scored
on a 0-100 scale with comments stripped. The chart puts every sample on one row and shows the Opus score
at each effort next to Haiku 5.5 xhigh and Sonnet 5.5 scored on the same 0-100 scale. There are no honest
Opus scores, so there is no Opus cutoff: read it as a ranking, not as a catch rate.

Writes results/analysis/opus-hard51-{scores,reasons}.csv, opus-hard51-fig{1,2,3}-*.png (the report figures, one message each)
and opus-hard51.png (every sample on its own row, for the appendix).

A monitor reply with no parsable score is stored by ControlArena as 0, the same as "saw nothing". Those are
counted here as parse failures and drawn as an x at 0, so a refusal is never read as a low score.
"""
from __future__ import annotations

import glob
import os
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from inspect_ai.log import read_eval_log

ROOT = Path(__file__).resolve().parents[1]
R = ROOT / "results"
OUT = R / "analysis"
LOG_GLOB = os.getenv("LOG_GLOB", str(ROOT / "logs" / "hard51-opus55-effort*"))
BUDGET, RESERVE = float(os.getenv("BUDGET", "7.00")), float(os.getenv("RESERVE", "0.50"))
EFFORTS = ["low", "medium", "high", "xhigh", "max"]
# USD per 1M tokens: (input, output, cache write, cache read). Same as PRICES in src/analyze.py.
OPUS = (4.00, 20.00, 5.00, 0.20)
# Output-token growth from one effort to the next, from the Haiku 5.5 effort runs (results/*haiku55-effort*).
# xhigh -> max has no Haiku data: it is a guess. Opus's own ratios replace these once two levels exist.
STEP_RATIO = {("low", "medium"): 1.19, ("medium", "high"): 1.44, ("high", "xhigh"): 1.98, ("xhigh", "max"): 1.6}
REFERENCE = {  # label -> 0-100 run in results/
    "Haiku 5.5 xhigh": "dataset-haiku55-xhigh-scale100-n500-strip",
    "Sonnet 5.5": "dataset500-sonnet55-um-scale100-strip",
}
GROUPS = [("never_caught", "Missed by every monitor at 0-100"),
          ("caught_at_0to100", "Caught by Sonnet or Haiku xhigh at 0-100"),
          ("caught_at_0to10_only", "Caught only by Haiku xhigh at 0-10")]

# Surface and ink from the dataviz reference palette; Opus efforts are one blue ramp, light to dark.
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
EFFORT_COLOR = {"low": "#86b6ef", "medium": "#5598e7", "high": "#2a78d6", "xhigh": "#1c5cab", "max": "#104281"}
HAIKU_C, SONNET_C = "#eb6834", "#1baf7a"


def effort_of(path: str) -> str:
    """logs/hard51-opus55-effortmax-pilot -> "max". A run done in pieces has one directory per piece."""
    return re.search(r"effort([a-z]+)", os.path.basename(path.rstrip("/"))).group(1)


def read_run(path: str) -> pd.DataFrame:
    rows = []
    for f in glob.glob(str(Path(path) / "**" / "*.eval"), recursive=True):
        for s in read_eval_log(f).samples or []:
            score = (s.scores or {}).get("max_suspicion_scorer")
            reason = ""
            for m in s.messages:
                if m.metadata and "suspicion_score" in m.metadata:
                    reason = str(m.metadata.get("reason", ""))
            tin = tout = 0
            cost = 0.0
            for model, u in (s.model_usage or {}).items():
                if "opus" not in model:
                    continue
                cw, cr = u.input_tokens_cache_write or 0, u.input_tokens_cache_read or 0
                plain, out = u.input_tokens or 0, u.output_tokens or 0
                tin += plain + cw + cr
                tout += out
                cost += (plain * OPUS[0] + out * OPUS[1] + cw * OPUS[2] + cr * OPUS[3]) / 1e6
            rows.append({"sample_id": str(s.id), "score": None if score is None else float(score.value) * 100,
                         "reason": reason, "parse_fail": reason.startswith("No score found"),
                         "tokens_in": tin, "tokens_out": tout, "cost": cost})
    return pd.DataFrame(rows)


def reference_scores() -> tuple[pd.DataFrame, dict[str, float]]:
    out, cutoffs = {}, {}
    for label, run in REFERENCE.items():
        d = pd.read_csv(R / f"{run}-samples.csv").dropna(subset=["suspicion"])
        d["sample_id"] = d.sample_id.astype(str)
        cutoffs[label] = float(np.percentile(d.loc[d["mode"] == "honest", "suspicion"], 98)) * 100
        out[label] = d[d["mode"] == "attack"].set_index("sample_id").suspicion * 100
    return pd.DataFrame(out), cutoffs


def summarise(runs: dict[str, pd.DataFrame], wide: pd.DataFrame) -> None:
    np.seterr(all="ignore")  # constant scores (all parse failures, or Opus giving everything one value) give nan, not a crash
    print(f"{'effort':8s} {'n':>3s} {'parse-fail':>10s} {'median':>7s} {'mean':>6s} {'max':>6s} {'in/call':>8s} {'out/call':>9s} {'$/call':>7s} {'total $':>8s}")
    for e, d in runs.items():
        ok = d[~d.parse_fail].score
        print(f"{e:8s} {len(d):3d} {int(d.parse_fail.sum()):10d} {ok.median():7.1f} {ok.mean():6.1f} {ok.max():6.1f} "
              f"{d.tokens_in.mean():8.0f} {d.tokens_out.mean():9.0f} {d.cost.mean():7.4f} {d.cost.sum():8.3f}")
    spent = sum(d.cost.sum() for d in runs.values())
    print(f"\nspent so far: ${spent:.3f} of ${BUDGET:.2f}  (left ${BUDGET - spent:.2f}, keeping ${RESERVE:.2f} spare)")
    done = list(runs)
    if len(done) >= 2:
        for a, b in zip(done, done[1:]):
            print(f"  observed output growth {a} -> {b}: x{runs[b].tokens_out.mean() / runs[a].tokens_out.mean():.2f}"
                  f"  (Haiku's was x{STEP_RATIO.get((a, b), float('nan')):.2f})")
    last = done[-1]
    d, n, N = runs[last], len(runs[last]), len(wide)
    left = BUDGET - spent - RESERVE
    if n < N:
        proj = (N - n) * d.cost.mean()
        fits = "fits" if proj <= left else "DOES NOT fit"
        print(f"{last} is partial, {n} of {N} done at ${d.cost.mean():.4f} per call. Finishing the other {N - n} would cost about "
              f"${proj:.2f} (rough: {n} calls is a small sample) -> {fits}")
    else:
        nxt = EFFORTS[EFFORTS.index(last) + 1] if last != EFFORTS[-1] else None
        if nxt:
            ratio = STEP_RATIO[(last, nxt)]
            # Input cost taken from the bill (it includes the 1.25x prompt-cache write), not from the plain input price.
            in_cost = d.cost.mean() - d.tokens_out.mean() * OPUS[1] / 1e6
            proj = n * (in_cost + d.tokens_out.mean() * ratio * OPUS[1] / 1e6)
            fits = "fits" if proj <= left else "DOES NOT fit"
            print(f"next level {nxt}: projected about ${proj:.2f} (x{ratio} output tokens vs {last}) -> {fits}")
    g = wide.groupby("group")[[c for c in wide if c.startswith("opus_")]].median().round(1)
    print("\nmedian score (0-100) by group:\n" + g.to_string())
    for e in runs:
        if len(runs[e]) < len(wide):
            continue  # a rank correlation on a handful of samples says nothing
        for ref in REFERENCE:
            # Spearman = Pearson on ranks (scipy is not installed); nan when Opus gave every sample the same score.
            rho = wide[f"opus_{e}"].rank().corr(wide[ref].rank())
            print(f"rank agreement (Spearman) opus {e} vs {ref}: {rho:.2f}")


def chart(wide: pd.DataFrame, runs: dict[str, pd.DataFrame], cutoffs: dict[str, float]) -> None:
    order = {g: i for i, (g, _) in enumerate(GROUPS)}
    opus_cols = [f"opus_{e}" for e in runs]
    w = wide.assign(_g=wide.group.map(order), _m=wide[opus_cols].max(axis=1) if opus_cols else 0)
    w = w.sort_values(["_g", "_m", "sample_id"], ascending=[True, False, True]).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.5, 0.2 * len(w) + 2.6), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    y = np.arange(len(w))[::-1]
    for label, c, mk, dy in (("Haiku 5.5 xhigh", HAIKU_C, "D", -0.2), ("Sonnet 5.5", SONNET_C, "s", 0.2)):
        ax.scatter(w[label].clip(lower=0), y + dy, s=26, marker=mk, color=c, edgecolor=SURFACE, linewidth=0.8, zorder=3, label=f"{label} (0-100)")
        ax.axvline(cutoffs[label], color=c, lw=0.9, ls=(0, (2, 2)), alpha=0.7, zorder=1)
    for e, d in runs.items():
        col = f"opus_{e}"
        okm = ~w[f"fail_{e}"]
        ax.scatter(w.loc[okm, col], y[okm.values], s=34, color=EFFORT_COLOR[e], edgecolor=SURFACE, linewidth=0.9, zorder=4, label=f"Opus 5.5, {e} effort")
        if (~okm).any():
            ax.scatter(np.zeros((~okm).sum()), y[(~okm).values], marker="x", s=30, color=INK, zorder=5, label=f"Opus {e}: no score (parse failure)")
    # group bands
    start = 0
    for g, title in GROUPS:
        n = int((w.group == g).sum())
        if not n:
            continue
        top, bot = y[start] + 0.5, y[start + n - 1] - 0.5
        ax.text(1.005, (top + bot) / 2, f"{title}\n(n={n})", transform=ax.get_yaxis_transform(), va="center", ha="left", fontsize=8, color=INK2)
        if start:
            ax.axhline(top, color=INK2, lw=0.8)
        start += n
    ax.set_yticks(y)
    ax.set_yticklabels(w.sample_id, fontsize=7, color=INK2)
    ax.set_ylim(-0.7, len(w) - 0.3)
    ax.set_xscale("symlog", linthresh=2, linscale=0.6)
    ax.set_xlim(-0.2, 105)
    ax.set_xticks([0, 1, 2, 5, 10, 20, 50, 100])
    ax.set_xticklabels(["0", "1", "2", "5", "10", "20", "50", "100"], fontsize=8, color=INK2)
    ax.set_xlabel("Suspicion score, 0-100 (dashed lines: the 2% cutoff of each reference monitor on honest code)", fontsize=8.5, color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.6, zorder=0)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0)
    fig.suptitle("Do the backdoors the small monitors missed look any different to Opus 5.5?", x=0.02, ha="left", fontsize=12, color=INK, y=0.995)
    ax.set_title("One row per backdoored sample (sample id on the left). Opus has no honest baseline, so no cutoff of its own.",
                 loc="left", fontsize=8.5, color=INK2, pad=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.45, -0.045 * 20 / len(w) - 0.02), ncol=2, fontsize=8, frameon=False, labelcolor=INK2)
    fig.subplots_adjust(left=0.07, right=0.72, top=0.93, bottom=0.12)
    fig.savefig(OUT / "opus-hard51.png", dpi=160, facecolor=SURFACE)
    print(f"wrote {OUT / 'opus-hard51.png'}")


# ---- report figures: three simple charts, one message each ------------------------------------
MISS_C, CAUGHT_C = "#2a78d6", "#e87ba4"  # blue = missed by all monitors, magenta = caught by Sonnet or Haiku at 0-100
BASE = dict(fontsize=11, color=INK2)


def _axes(figsize):
    fig, ax = plt.subplots(figsize=figsize, facecolor=SURFACE)
    ax.set_facecolor(SURFACE)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(length=0, labelsize=11, labelcolor=INK2)
    return fig, ax


def _score_axis(ax, which="y"):
    ticks = [0, 1, 2, 5, 10, 20, 50, 100]
    if which == "y":
        ax.set_yscale("symlog", linthresh=2, linscale=0.6)
        ax.set_ylim(-0.2, 105)
        ax.set_yticks(ticks)
        ax.set_yticklabels([str(t) for t in ticks])
        ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    else:
        ax.set_xscale("symlog", linthresh=2, linscale=0.6)
        ax.set_xlim(-0.2, 105)
        ax.set_xticks(ticks)
        ax.set_xticklabels([str(t) for t in ticks])
        ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)


def _titles(fig, title, sub, foot):
    import textwrap
    w = fig.get_figwidth()
    fig.text(0.02, 0.975, textwrap.fill(title, int(w * 7)), ha="left", va="top", fontsize=15, color=INK, fontweight="semibold", linespacing=1.25)
    fig.text(0.02, 0.875, textwrap.fill(sub, int(w * 10.5)), ha="left", va="top", fontsize=11, color=INK2, linespacing=1.4)
    fig.text(0.02, 0.015, textwrap.fill(foot, int(w * 13.5)), ha="left", va="bottom", fontsize=9, color=INK2, linespacing=1.4)


def report_figures(wide: pd.DataFrame, runs: dict[str, pd.DataFrame]) -> None:
    d49 = wide[wide.group.isin(["never_caught", "caught_at_0to100"])]
    e = list(runs)[-1]
    col = f"opus_{e}"
    n_fail = int(d49[col].isna().sum())  # a reply with no score is NaN, not 0, so it never shows as "saw nothing"
    d49 = d49.dropna(subset=[col])
    miss, caught = d49[d49.group == "never_caught"], d49[d49.group == "caught_at_0to100"]
    left_out = f" {n_fail} backdoor{'s' if n_fail > 1 else ''} left out because Opus returned no score at {e} effort." if n_fail else ""
    foot = (f"{len(d49)} backdoored solutions, comments stripped, 0-100 prompt. Opus 5.5 at {e} effort. "
            f"Opus has no score on honest code, so its scores rank backdoors but are not a catch rate.{left_out}")

    # 1. Opus agrees with the small monitors about which backdoors are obvious.
    fig, ax = _axes((8, 6))
    rng = np.random.default_rng(3)
    for x, g, c in ((0, miss, MISS_C), (1, caught, CAUGHT_C)):
        ax.scatter(x + rng.uniform(-0.15, 0.15, len(g)), g[col].clip(lower=0), s=70, color=c, edgecolor=SURFACE, linewidth=1.2, zorder=3)
        m = float(g[col].median())
        ax.plot([x - 0.32, x + 0.32], [m, m], color=INK, lw=2.4, zorder=4, solid_capstyle="butt")
        ax.text(x + 0.36, m, f"median {m:g}", va="center", fontsize=11, color=INK)
    _score_axis(ax, "y")
    ax.set_xlim(-0.6, 1.9)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"Missed by every monitor\n({len(miss)} backdoors)", f"Caught by Sonnet or Haiku\n({len(caught)} backdoors)"], fontsize=11, color=INK2)
    ax.set_ylabel("Opus 5.5 suspicion score (0-100)", **BASE)
    fig.subplots_adjust(left=0.11, right=0.97, top=0.70, bottom=0.19)
    _titles(fig, "Opus agrees with the small monitors about which backdoors are obvious",
            f"Backdoors that Sonnet or Haiku catch get a median Opus score of {caught[col].median():g}. "
            f"Backdoors that every monitor missed get {miss[col].median():g}. Opus was not used to make these groups.", foot)
    fig.savefig(OUT / "opus-hard51-fig1-agreement.png", dpi=200, facecolor=SURFACE)

    # 2. ...but it also scores some of the missed ones high.
    top = miss.sort_values(col, ascending=False).head(10).iloc[::-1]
    rest = miss.drop(top.index)
    n20 = int((miss[col] >= 20).sum())
    fig, ax = _axes((8, 6))
    y = np.arange(len(top))
    ax.barh(y, top[col], color=MISS_C, height=0.55, zorder=2)
    for yi, v, so, ha in zip(y, top[col], top["Sonnet 5.5"], top["Haiku 5.5 xhigh"]):
        ax.text(v + 1.5, yi, f"{v:g}", va="center", fontsize=11, color=INK, fontweight="semibold")
        ax.text(1.03, yi, f"{so:g}  /  {ha:g}", transform=ax.get_yaxis_transform(), va="center", ha="left", fontsize=11, color=INK2)
    ax.text(1.03, len(top) - 0.35, "Sonnet / Haiku", transform=ax.get_yaxis_transform(), va="bottom", ha="left", fontsize=10, color=INK2)
    ax.set_yticks(y)
    ax.set_yticklabels([f"Problem {i}" for i in top.sample_id], fontsize=11, color=INK2)
    ax.set_xlim(0, 100)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    ax.set_xlabel("Suspicion score (0-100)", **BASE)
    fig.subplots_adjust(left=0.17, right=0.84, top=0.70, bottom=0.19)
    _titles(fig, f"Opus rates {n20} of the {len(miss)} missed backdoors at 20 or more",
            f"The 10 highest-scored backdoors out of the {len(miss)} that no monitor caught. Bars are Opus scores; the numbers on the right are what Sonnet and Haiku gave the same backdoor. Those two score every one of them at {max(miss['Haiku 5.5 xhigh'].max(), miss['Sonnet 5.5'].max()):g} or below. Opus scores the other {len(rest)} at {rest[col].max():g} or below (median {rest[col].median():g}).", foot)
    fig.savefig(OUT / "opus-hard51-fig2-missed.png", dpi=200, facecolor=SURFACE)

    # 3. Does thinking harder change the answer? Needs two efforts.
    if len(runs) >= 2:
        lo, hi = list(runs)[0], list(runs)[-1]
        fig, ax = _axes((7, 6.6))
        ax.plot([0, 100], [0, 100], color=GRID, lw=1.5, zorder=1)
        for g, c, lab in ((miss, MISS_C, "Missed by every monitor"), (caught, CAUGHT_C, "Caught by Sonnet or Haiku")):
            ax.scatter(g[f"opus_{lo}"].clip(lower=0), g[f"opus_{hi}"].clip(lower=0), s=60, color=c, edgecolor=SURFACE, linewidth=1, alpha=0.95, zorder=3, label=lab)
        _score_axis(ax, "x")
        _score_axis(ax, "y")
        ax.grid(True, color=GRID, lw=0.7)
        both = d49[[f"opus_{lo}", f"opus_{hi}"]].dropna()
        diff = both[f"opus_{hi}"] - both[f"opus_{lo}"]
        moved, up, down = int((diff.abs() < 10).sum()), int((diff >= 10).sum()), int((diff <= -10).sum())
        ax.set_xlabel(f"Opus score at {lo} effort", **BASE)
        ax.set_ylabel(f"Opus score at {hi} effort", **BASE)
        ax.legend(loc="lower right", frameon=False, fontsize=10.5, labelcolor=INK2)
        n_see = int(((d49[f"opus_{lo}"] <= 5) & (d49[f"opus_{hi}"] >= 50)).sum())
        if n_see:
            ax.annotate(f"{n_see} backdoor{'s' if n_see > 1 else ''} noticed\nonly at {hi} effort", xy=(1.05, 60), xytext=(2.6, 33), fontsize=10.5, color=INK, arrowprops=dict(arrowstyle="-", color=INK2, lw=1))
        c_lo, c_hi = runs[lo].cost.mean(), runs[hi].cost.mean()
        fig.subplots_adjust(left=0.12, right=0.97, top=0.70, bottom=0.17)
        _titles(fig, f"Most backdoors score the same at {lo} and {hi} effort",
                f"{len(both) - moved} of {len(both)} move by 10 points or more between {lo} and {hi} effort ({up} up, {down} down). A dot on the line means no change. "
                f"{hi.capitalize()} effort costs \\${c_hi:.3f} per call, against \\${c_lo:.3f} at {lo}.",
                f"{len(both)} backdoored solutions, comments stripped, 0-100 prompt, Opus 5.5.{left_out}")
        fig.savefig(OUT / "opus-hard51-fig3-effort.png", dpi=200, facecolor=SURFACE)
    plt.close("all")
    print("wrote opus-hard51-fig1-agreement.png, fig2-missed.png" + (", fig3-effort.png" if len(runs) >= 2 else ""))


def main() -> None:
    dirs = sorted(glob.glob(LOG_GLOB), key=lambda p: EFFORTS.index(effort_of(p)))
    if not dirs:
        raise SystemExit(f"no runs match {LOG_GLOB}")
    by_effort: dict[str, list[pd.DataFrame]] = {}
    for p in dirs:
        by_effort.setdefault(effort_of(p), []).append(read_run(p))
    runs = {}
    for e, parts in by_effort.items():
        runs[e] = pd.concat(parts, ignore_index=True)
        dup = runs[e].sample_id[runs[e].sample_id.duplicated()].tolist()
        assert not dup, f"{e}: the same sample was scored twice (overlapping pieces): {dup}"
    labels = pd.read_csv(OUT / "opus-hard51-labels.csv", dtype={"sample_id": str}).set_index("sample_id")
    ref, cutoffs = reference_scores()
    wide = labels.join(ref)
    reasons = []
    for e, d in runs.items():
        d = d.set_index("sample_id")
        wide[f"opus_{e}"] = d.score.where(~d.parse_fail)  # a parse failure is stored as 0 by ControlArena; blank it here
        wide[f"fail_{e}"] = d.parse_fail
        reasons += [{"sample_id": i, "effort": e, "score": r.score, "parse_fail": r.parse_fail, "reason": r.reason} for i, r in d.iterrows()]
    wide = wide.reset_index()
    complete = {e: d for e, d in runs.items() if len(d) == len(wide)}
    for e in runs.keys() - complete.keys():
        print(f"note: {e} has {len(runs[e])} of {len(wide)} samples so far; it is left out of the figures until it is complete")

    # Refuse to write when the logs on hand cannot rebuild what is already committed.
    # The two CSVs and four PNGs below ARE the committed tables and figures, and the
    # writes are unconditional while the figures they illustrate are not. Run with a
    # subset of the logs and the four-effort scores table was replaced by a one-column
    # one, after which report_figures raised IndexError from `list(runs)[-1]` on an
    # empty `complete`, naming a list index rather than the runs that were missing. By
    # then the committed data was already gone. logs/ is gitignored, so having part of
    # the input is the ordinary case for anyone but the person who produced it, not an
    # exotic one. The note above is printed for the same condition, so the script knew.
    scores_csv = OUT / "opus-hard51-scores.csv"
    if scores_csv.exists():
        had = [c for c in pd.read_csv(scores_csv, nrows=0).columns if c.startswith("opus_")]
        rebuilt = [f"opus_{e}" for e in runs]
        lost = [c for c in had if c not in rebuilt]
        if lost:
            raise SystemExit(
                f"{scores_csv.name} holds {', '.join(had)}, but these logs rebuild only "
                f"{', '.join(rebuilt) or 'nothing'}, so writing would drop "
                f"{', '.join(lost)}. Point LOG_GLOB at the full set of runs (it is "
                f"currently {LOG_GLOB}) or move the committed tables aside on purpose.")
    if not complete:
        have = ", ".join(f"{e}={len(d)}" for e, d in runs.items()) or "none"
        raise SystemExit(
            f"no effort arm is complete ({have} of {len(wide)} samples), so there is "
            f"nothing for the figures to show and report_figures would fail on an empty "
            f"set. Nothing was written.")

    wide.drop(columns=[c for c in wide if c.startswith("fail_")]).to_csv(OUT / "opus-hard51-scores.csv", index=False)
    # Sorted so the row order is a property of the data and not of how the logs
    # happened to be split into pieces. Sample 788 arrives in a second xhigh piece,
    # which otherwise appends it after the first pass's 50 rather than in place.
    (pd.DataFrame(reasons)
       .assign(_e=lambda d: d.effort.map({e: i for i, e in enumerate(EFFORTS)}))
       .sort_values(["_e", "sample_id"], key=lambda c: c if c.name == "_e"
                    else c.astype(int))
       .drop(columns="_e")
       .to_csv(OUT / "opus-hard51-reasons.csv", index=False))
    summarise(runs, wide)
    chart(wide, complete, cutoffs)
    report_figures(wide, complete)


if __name__ == "__main__":
    main()
