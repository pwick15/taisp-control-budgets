"""M03: how wide a paired comparison's interval is, against how many honest rows its cutoff rests on."""
import zlib

import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M03",
    "title": "Wide intervals come from too few honest programs",
    "section": "appendix",
    "order": 134,
    "caption": ("One dot per pairwise comparison in MATCHED-FPR: how many honest programs sit above the "
                "shared cutoff, against the width of the 95% interval on the recall gap. The dashed line "
                "is this project's bar of five honest rows; the stepped line is the median at each count."),
    "notes": [
        "The median interval runs {w1} points wide when the cutoff rests on one honest row and {w5} at "
        "five. Nothing about the monitors changes along this axis; only how much honest data the "
        "threshold was estimated from.",
        "Data quality, which is the point of this figure: {n_thin} of {n} comparisons rest on fewer than "
        "five honest rows, and only {n_sep} of {n} separate from zero at all.",
        "No comparison rests on exactly four honest rows, and none rests on more than five. The gaps are "
        "real, not missing data: a rung exists only where both monitors can serve the same rate exactly.",
        "This figure used to reach 46 honest rows. That comparison, Sonnet against the Gemma 3 4B 0-100 "
        "arm, left the set when the parser-default repairs landed: one corrected honest score moved that "
        "arm's achievable rate and the shared rung disappeared. M09 and MATCHED-FPR record it.",
        "Ported from the data explorer's e3-width-vs-rows view, reading the committed pairwise table.",
    ],
    "height": 500,
}

BAR = 5


def build() -> Figure:
    p = pd.read_csv(S.ANALYSIS / "matched-fpr-pairwise.csv")
    pts = []
    for r in p.itertuples():
        j = float(np.random.default_rng(zlib.crc32(f"{r.other}{r.shared_fpr_pct}".encode()))
                  .uniform(-0.18, 0.18))
        pts.append({"value": [round(int(r.honest_rows_above_cutoff) + j, 3), round(float(r.ci_width_pts), 2)],
                    "tip": (f"<b>{r.reference} vs {r.other}</b><br>shared FPR {r.shared_fpr_pct:g}%"
                            f"<br>{int(r.honest_rows_above_cutoff)} honest row(s) above the cutoff"
                            f"<br>gap {r.gap_pts:+.1f}, interval {r.ci_width_pts:.1f} points wide")})
    med = p.groupby("honest_rows_above_cutoff").ci_width_pts.median().reset_index()
    option = C.base(
        grid={"left": 74, "right": 32, "top": 40, "bottom": 58},
        xAxis=C.axis("Honest programs above the shared cutoff", type="value", min=0.4, max=5.8,
                     axisLabel={"formatter": "function (v) { return v % 1 ? '' : v; }"}),
        yAxis=C.axis("Width of the 95% interval (points)", gap=52, type="value", min=0,
                     max=float(np.ceil(p.ci_width_pts.max() / 10) * 10)),
        legend={"top": 0, "left": 68, "data": ["one comparison", "median at that count"]},
        series=[
            {"name": "one comparison", "type": "scatter", "symbolSize": 10, "data": pts,
             "itemStyle": {"color": "@context-strong", "opacity": 0.7,
                           "borderColor": "@ink-surface", "borderWidth": 1},
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1.5},
                          "label": {"show": False}, "data": [{"xAxis": BAR}]}},
            {"name": "median at that count", "type": "line", "step": "middle", "symbolSize": 9,
             "lineStyle": {"color": "@s0", "width": 2.5}, "itemStyle": {"color": "@s0"},
             "data": [{"value": [int(r.honest_rows_above_cutoff), round(float(r.ci_width_pts), 2)],
                       "tip": f"median {r.ci_width_pts:.1f} points at {int(r.honest_rows_above_cutoff)} row(s)"}
                      for r in med.itertuples()]},
        ],
    )
    rows = [{"reference": r.reference, "other": r.other, "shared_fpr_pct": r.shared_fpr_pct,
             "honest_rows_above_cutoff": int(r.honest_rows_above_cutoff),
             "ci_width_pts": float(r.ci_width_pts), "separated": bool(r.separated)}
            for r in p.itertuples()]
    facts = {"n": len(p), "n_sep": int(p.separated.sum()),
             "n_thin": int((p.honest_rows_above_cutoff < BAR).sum()),
             "w1": round(float(p[p.honest_rows_above_cutoff == 1].ci_width_pts.median()), 1),
             "w5": round(float(p[p.honest_rows_above_cutoff >= BAR].ci_width_pts.median()), 1)}
    return Figure(option=option, data=rows, facts=facts)
