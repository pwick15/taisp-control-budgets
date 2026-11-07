"""M04: what a wider score scale buys each monitor, in usable cutoffs and in the tightest budget."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from analysis_score_resolution import MIN_HONEST_ROWS, PAIRS  # noqa: E402

META = {
    "id": "M04",
    "title": "A wider score scale adds usable cutoffs for every monitor",
    "section": "appendix",
    "order": 138,
    "caption": ("Left: how many audit rates a monitor can actually be placed at, counting only cutoffs "
                "resting on at least {bar} honest programs. Right: the cheapest of those rates. Each line "
                "is one monitor asked for the same judgement on a wider scale. Dashed lines are pairs that "
                "change something else too."),
    "notes": [
        "Usable cutoffs rise on {n_up} of the {n_clean} clean pairs, and the cheapest usable rate falls "
        "on {n_lower}. Nothing about the model changes along these lines; only the scale it was asked to "
        "answer on.",
        "Two pairs are drawn dashed because they are confounded, not clean: gpt-oss-120b and Qwen 3.8 "
        "Omni Flash each changed reasoning effort as well as the scale, so their movement is not the "
        "prompt's doing. They are excluded from the counts above, as in SCORE-SCALE.md.",
        "A cutoff counts as usable when at least {bar} honest programs sit above it. That bar is the "
        "whole reason this figure is not just a count of distinct scores: M03 shows what intervals look "
        "like below it.",
        "The pairs and the usable rule are imported from scripts/analysis_score_resolution.py, so this "
        "figure and SCORE-SCALE.md cannot drift apart.",
        "Rebuilt from committed per-sample tables, replacing the exported snapshot.",
    ],
    "height": 560,
}

SCALES = [10, 100, 200]
COLOURS = ["@s0", "@s1", "@s2", "@s6", "@s4", "@s3", "@context-strong", "@context-strong"]


def describe(run: str) -> dict | None:
    try:
        d = pd.read_csv(S.RESULTS / f"{run}-samples.csv")
    except FileNotFoundError:
        return None
    honest = d[d["mode"] == "honest"].suspicion.dropna().to_numpy()
    if not len(honest):
        return None
    achievable = sorted({(honest > v).mean() for v in np.unique(honest)})
    usable = [f for f in achievable if 0 < f <= 0.5 and f * len(honest) >= MIN_HONEST_ROWS]
    return {"usable": len(usable), "lowest": 100 * min(usable) if usable else None}


def build() -> Figure:
    by_mon: dict[str, dict] = {}
    for mon, scale, base, wider, note in PAIRS:
        e = by_mon.setdefault(mon, {"runs": {}, "note": ""})
        e["runs"][10] = base
        e["runs"][scale] = wider
        if note:
            e["note"] = note
    series, rows, up, lower, clean = [], [], 0, 0, 0
    for i, (mon, e) in enumerate(by_mon.items()):
        got = {s: describe(r) for s, r in e["runs"].items()}
        got = {s: v for s, v in got.items() if v}
        if 10 not in got or len(got) < 2:
            continue
        dashed = bool(e["note"])
        if not dashed:
            clean += 1
            up += any(got[s]["usable"] > got[10]["usable"] for s in got if s != 10)
            lows = [got[s]["lowest"] for s in got if s != 10 and got[s]["lowest"] is not None]
            if got[10]["lowest"] is not None and lows and min(lows) < got[10]["lowest"]:
                lower += 1
        style = {"color": COLOURS[i % len(COLOURS)], "width": 2.5,
                 **({"type": "dashed"} if dashed else {})}
        for panel, (field, unit) in enumerate((("usable", "cutoffs"), ("lowest", "%"))):
            pts = [{"value": [SCALES.index(s), got[s][field]],
                    "tip": (f"<b>{mon}</b><br>0-{s} prompt<br>{got[s]['usable']} usable cutoffs"
                            + (f"<br>cheapest {got[s]['lowest']:.2f}%" if got[s]["lowest"] else "")
                            + (f"<br>confounded: {e['note']}" if dashed else ""))}
                   for s in SCALES if s in got and got[s][field] is not None]
            series.append({"name": mon, "type": "line", "xAxisIndex": panel, "yAxisIndex": panel,
                           "symbolSize": 9, "lineStyle": style,
                           "itemStyle": {"color": style["color"], "borderColor": "@ink-surface",
                                         "borderWidth": 1.5},
                           "data": pts, "connectNulls": True})
        rows += [{"monitor": mon, "scale": f"0-{s}", "run": e["runs"][s],
                  "usable_cutoffs": got[s]["usable"], "cheapest_usable_pct": got[s]["lowest"],
                  "confounded": dashed} for s in SCALES if s in got]
    labels = [f"0-{s}" for s in SCALES]
    option = C.base(
        grid=[{"left": 68, "right": "56%", "top": 58, "bottom": 56},
              {"left": "56%", "right": 32, "top": 58, "bottom": 56}],
        xAxis=[C.axis("Score scale asked for", type="category", data=labels, boundaryGap=False),
               C.axis("Score scale asked for", type="category", data=labels, gridIndex=1,
                      boundaryGap=False)],
        yAxis=[C.axis("Usable cutoffs", gap=44, type="value", min=0),
               C.axis("Cheapest usable rate", gap=52, type="value", gridIndex=1,
                      axisLabel={"formatter": "{value}%"})],
        legend={"top": 0, "left": 62, "data": list(by_mon)},
        series=series,
    )
    facts = {"bar": MIN_HONEST_ROWS, "n_clean": clean, "n_up": up, "n_lower": lower}
    return Figure(option=option, data=rows, facts=facts)
