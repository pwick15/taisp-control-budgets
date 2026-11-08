"""M06: one audit budget, spent on a single monitor's cutoff or split across several."""
import itertools

import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M06",
    "title": "Splitting the audit budget across monitors buys very little",
    "section": "appendix",
    "order": 140,
    "caption": ("One budget, spent two ways. The dashed line is the best a single cutoff can do; the "
                "solid line is the best an OR of up to this many monitors can do for the same honest "
                "false positives in total. Use the dial to change how many you may buy."),
    "notes": [
        "The most any ensemble buys anywhere on this grid is {best_gain} points, and at the tightest "
        "budget it buys nothing at all: {tight}% is too little to split.",
        "This is an upper bound, not a protocol. Both the monitors and their cutoffs are chosen knowing "
        "which programs are backdoored, so the curve is fitted on the data it is scored on. A real "
        "ensemble picked in advance would do worse.",
        "The union's false-positive rate is measured, not added: every arm scored the same 500 honest "
        "programs, so overlapping alarms are counted once. That is what makes the comparison fair.",
        "The pool is one arm per monitor family, the 0 to 10 stripped arm with the best separation: "
        "{pool}.",
        "Rebuilt from committed per-sample tables, replacing the exported snapshot.",
    ],
    "height": 520,
}

GRID = [0.5, 1.0, 2.0, 3.0, 5.0, 7.5, 10.0]
KS = [1, 2, 3, 4]


def bits(mask: np.ndarray) -> int:
    n = 0
    for i, v in enumerate(mask):
        if v:
            n |= 1 << i
    return n


def build() -> Figure:
    chosen = S.family_pool()
    runs = list(chosen.values())
    h0, a0 = S.load_scores(runs[0])
    ids_h, ids_a = sorted(h0.index), sorted(a0.index)
    nh, na = len(ids_h), len(ids_a)
    cand: dict[str, list] = {}
    for r in runs:
        h, a = S.load_scores(r)
        hv, av = h.reindex(ids_h).to_numpy(float), a.reindex(ids_a).to_numpy(float)
        rows = []
        for v in np.unique(hv):
            hm = hv > v
            f = 100.0 * hm.sum() / nh
            if 0 < f <= max(GRID) + 1e-9:
                rows.append((f, bits(hm), bits(av > v)))
        cand[r] = rows
    best: dict[tuple[int, float], tuple[float, tuple]] = {}
    for k in KS:
        for b in GRID:
            top = (-1.0, ())
            for combo in itertools.combinations(runs, k):
                lists = [[c for c in cand[r] if c[0] <= b + 1e-9] for r in combo]
                if any(not L for L in lists):
                    continue
                for choice in itertools.product(*lists):
                    hb = ab = 0
                    for c in choice:
                        hb |= c[1]
                        ab |= c[2]
                    served = 100.0 * hb.bit_count() / nh
                    if served > b + 1e-9:
                        continue
                    rec = ab.bit_count() / na
                    if rec > top[0]:
                        top = (rec, (combo, served))
            best[(k, b)] = top
    name = {v: k for k, v in chosen.items()}
    one = [best[(1, b)][0] for b in GRID]
    frames, rows = [], []
    for k in KS:
        here = [best[(k, b)] for b in GRID]
        frames.append({"series": [
            {"name": "best single cutoff", "type": "line", "symbolSize": 7,
             "lineStyle": {"color": "@context-strong", "width": 2, "type": "dashed"},
             "itemStyle": {"color": "@context-strong"},
             "data": [{"value": [b, round(100 * v, 2)], "tip": f"one monitor at {b:g}%: {100 * v:.1f}%"}
                      for b, v in zip(GRID, one)]},
            {"name": "best ensemble", "type": "line", "symbolSize": 8,
             "lineStyle": {"color": "@s0", "width": 2.5},
             "itemStyle": {"color": "@s0", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "data": [{"value": [b, round(100 * rec, 2)],
                       "tip": (f"<b>{b:g}% budget, up to {k}</b><br>{100 * rec:.1f}% caught"
                               f"<br>{', '.join(name[r] for r in info[0])}"
                               f"<br>served {info[1]:.2f}%")}
                      for b, (rec, info) in zip(GRID, here)]}]})
        rows += [{"max_monitors": k, "budget_pct": b, "ensemble_recall": round(rec, 4),
                  "best_single_recall": round(o, 4), "gain_pts": round(100 * (rec - o), 2),
                  "monitors": ", ".join(name[r] for r in info[0]), "served_pct": round(info[1], 3)}
                 for b, (rec, info), o in zip(GRID, here, one)]
    gain = max(100 * (best[(k, b)][0] - best[(1, b)][0]) for k in KS for b in GRID)
    facts = {"best_gain": round(gain, 1), "tight": f"{min(GRID):g}",
             "pool": ", ".join(chosen)}
    option = C.base(
        grid={"left": 70, "right": 32, "top": 40, "bottom": 58},
        xAxis=C.axis("Total audit budget (log scale)", type="log", min=0.5, max=10,
                     axisLabel={"formatter": "{value}%"}),
        yAxis=C.axis("Backdoors caught", gap=48, type="value", min=75, max=95,
                     axisLabel={"formatter": "{value}%"}),
        legend={"top": 0, "left": 64, "data": ["best single cutoff", "best ensemble"]},
        series=frames[1]["series"],
    )
    return Figure(option=option, data=rows, facts=facts,
                  dial={"label": "Monitors you may buy", "steps": [str(k) for k in KS],
                        "initial": 1, "frames": frames})
