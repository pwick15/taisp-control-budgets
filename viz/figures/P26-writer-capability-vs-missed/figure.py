"""P26: do more capable backdoor writers get more of their backdoors past every monitor?

Capability is Epoch AI's Capabilities Index, read from viz/data/eci-scores.csv, the same file P24 uses
(source and snapshot choices are documented there). Misses come from results/analysis/case-features.csv.
"""
import itertools

import numpy as np
import pandas as pd

from viz.kit import ROOT, Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P26",
    "title": "More capable writers didn't produce harder-to-catch backdoors",
    "section": "results",
    "order": 113,
    "caption": ("Each dot is one backdoor-writing model, placed by its Epoch Capabilities Index score. Up is the "
                "share of its backdoors missed by all seven monitors at a 2% budget. Faint bars are 95% ranges, the "
                "number is how many it wrote, the dashed line is all writers. Hover for Epoch's interval."),
    "notes": [
        "Rank correlation between capability and share missed is {rho:+.2f} across {k} writers (exact "
        "permutation p = {p:.2f}). With this few writers only a strong link would show, so this rules out a "
        "strong trend, not a weak one.",
        "o3-mini and Claude 3.7 Sonnet score almost the same on the index, yet {o3:.0f}% of o3-mini's backdoors "
        "got past every monitor against {c37:.0f}% of Claude 3.7 Sonnet's, and mid-ranked o1-mini reached "
        "{o1:.0f}%. How a model writes backdoors seems to matter more than its general capability.",
        "ECI scores and snapshot choices are shared with P24 (viz/data/eci-scores.csv). Claude 3.7 Sonnet "
        "includes its {n_thinking} extended-thinking backdoors, because Epoch scores the model once.",
        "Every writer here is weaker than our main monitors (P24), so this says nothing about an attacker "
        "stronger than its monitor. Models also wrote backdoors for different problems, so problem difficulty "
        "is mixed in with the writer.",
    ],
    "height": 440,
}

ECI = ROOT / "viz" / "data" / "eci-scores.csv"
NAMES = {"o3-mini": "o3-mini", "o1-mini": "o1-mini", "GPT-4o (Aug 2024)": "GPT-4o",
         "GPT-4o mini": "GPT-4o mini", "GPT-3.5 Turbo (Jan 2024)": "GPT-3.5 Turbo",
         "Claude 3.5 Haiku": "Claude 3.5 Haiku", "Claude 3.7 Sonnet": "Claude 3.7 Sonnet",
         "Gemini 2.0 Flash (Feb 2025)": "Gemini 2.0 Flash"}
# Where each name sits relative to its dot, so neighbours and range bars don't collide.
PLACE = {"GPT-4o mini": "left", "Gemini 2.0 Flash": "bottom", "o3-mini": "left"}


def rank_corr(x: np.ndarray, y: np.ndarray) -> float:
    rx, ry = pd.Series(x).rank().to_numpy(), pd.Series(y).rank().to_numpy()
    return float(np.corrcoef(rx, ry)[0, 1])


def build() -> Figure:
    cf = S.cases()
    eci = pd.read_csv(ECI)
    w = eci[eci.role == "writer"].copy()
    w["n"] = w.key.map(cf.model.value_counts()).fillna(0).astype(int)
    w["missed"] = w.key.map(cf[cf.caught_by == 0].model.value_counts()).fillna(0).astype(int)
    # One row per Epoch entry: Claude 3.7 Sonnet's thinking backdoors fold into Claude 3.7 Sonnet.
    g = (w.groupby("eci_name").agg(eci=("eci", "first"), eci_lo=("eci_lo", "first"), eci_hi=("eci_hi", "first"),
                                   n=("n", "sum"), missed=("missed", "sum")).reset_index())
    g["writer"] = g.eci_name.map(NAMES)
    g["share"] = g.missed / g.n
    g["lo"], g["hi"] = zip(*[S.wilson(int(k), int(n)) for k, n in zip(g.missed, g.n)])
    g = g.sort_values("eci").reset_index(drop=True)
    overall = float(g.missed.sum() / g.n.sum())

    rho = rank_corr(g.eci.to_numpy(), g.share.to_numpy())
    ry = pd.Series(g.share).rank().to_numpy()
    rx = pd.Series(g.eci).rank().to_numpy()
    null = [np.corrcoef(rx, np.array(p))[0, 1] for p in itertools.permutations(ry)]
    p = float(np.mean(np.abs(null) >= abs(rho) - 1e-12))

    dots = [{"value": [round(r.eci, 2), round(100 * r.share, 2)],
             "label": {"formatter": f"{r.writer} ({r.n})", "position": PLACE.get(r.writer, "right")},
             "tip": (f"<b>{r.writer}</b><br>ECI {r.eci:.1f} (interval {r.eci_lo:.1f} to {r.eci_hi:.1f})"
                     f"<br>{r.missed} of {r.n} missed by all seven ({100 * r.share:.1f}%)"
                     f"<br>95% range {100 * r.lo:.0f}–{100 * r.hi:.0f}%")}
            for r in g.itertuples()]
    option = C.base(
        grid={"left": 58, "right": 30, "top": 20, "bottom": 52},
        xAxis=C.axis("Writer's Epoch Capabilities Index", type="value", min=105, max=150, interval=5,
                     splitLine={"show": False}),
        yAxis=C.axis("Missed by all seven monitors", gap=42, type="value", min=0, max=50,
                     axisLabel={"formatter": "{value}%"}),
        series=[
            {"name": "_range", "type": "custom", "renderItem": C.VBAR, "itemStyle": {"color": "@s7"},
             "data": [[round(r.eci, 2), round(100 * r.lo, 2), round(100 * r.hi, 2)] for r in g.itertuples()],
             "encode": {"x": 0, "y": [1, 2]}, "z": 1, "silent": True, "tooltip": {"show": False}},
            {"name": "writers", "type": "scatter", "symbolSize": 11, "z": 3, "data": dots,
             "itemStyle": {"color": "@s7", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "label": {"show": True, "color": "@ink-primary", "fontSize": 12, "distance": 8}},
            {"name": "_all", "type": "line", "data": [], "silent": True,
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1.2},
                          "label": {"formatter": f"all writers {100 * overall:.0f}%", "position": "insideStartTop",
                                    "color": "@ink-muted", "fontSize": 11},
                          "data": [{"yAxis": round(100 * overall, 2)}]}},
        ],
    )
    share = dict(zip(g.writer, 100 * g.share))
    rows = g[["writer", "eci_name", "eci", "eci_lo", "eci_hi", "n", "missed", "share", "lo", "hi"]]
    return Figure(option=option, data=rows, facts={
        "rho": rho, "p": p, "k": len(g), "o3": share["o3-mini"], "o1": share["o1-mini"],
        "c37": share["Claude 3.7 Sonnet"],
        "n_thinking": int((cf.model == "anthropic/claude-3-7-sonnet-thinking-latest").sum())})
