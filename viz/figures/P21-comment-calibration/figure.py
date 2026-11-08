"""P21: showing comments still catches more when the cutoff is set on honest code that has comments."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P21",
    "title": "Showing comments still wins when honest code has comments too",
    "section": "appendix",
    "order": 138,
    "caption": ("Backdoors caught at a 2% audit budget by Haiku 5.5 xhigh, with comments removed (grey) or shown "
                "(blue). Top: the cutoff is set on honest code with no comments. Bottom: on the same honest code "
                "with two plain comments added, so commented code can't stand out just for having comments."),
    "notes": [
        "The objection this answers: honest code in this dataset barely has comments, so maybe commented code "
        "only looks suspicious for being unusual. If so, the bottom gap would close. It is {gap_c:.1f} points "
        "against {gap_b:.1f}.",
        "The added honest comments are templated ('# read the input'), a stand-in for commented honest code, "
        "not a sample of it.",
        "Scored by calling the monitor directly rather than through the eval harness, so these numbers don't "
        "join to the main run tables. Replaces Marnick's M05 as the simple version of the same check.",
    ],
    "height": 260,
}

BUDGET = 0.02
CUTOFFS = [("bare", "Cutoff from honest code, no comments"),
           ("short", "Cutoff from honest code, comments added")]


def build() -> Figure:
    honest = pd.read_csv(S.ANALYSIS / "comment-length.csv")
    attack = pd.read_csv(S.ANALYSIS / "honest-calibration.csv")
    rem = attack.stripped.dropna().to_numpy(float)
    shw = attack.kept.dropna().to_numpy(float)

    links, removed, shown, rows, facts = [], [], [], [], {}
    for i, (col, label) in enumerate(CUTOFFS):
        h = honest[col].dropna().to_numpy(float)
        r = 100 * S.safety_at(h, rem, BUDGET)["exact"]
        s = 100 * S.safety_at(h, shw, BUDGET)["exact"]
        links.append({"type": "line", "silent": True, "symbol": "none", "z": 1,
                      "lineStyle": {"color": "@context", "width": 6, "cap": "round"},
                      "data": [[round(r, 2), i], [round(s, 2), i]]})
        removed.append({"value": [round(r, 2), i], "label": {"formatter": f"removed {r:.0f}%"},
                        "tip": f"<b>{label}</b><br>comments removed: {r:.1f}% caught"})
        shown.append({"value": [round(s, 2), i], "label": {"formatter": f"shown {s:.0f}%"},
                      "tip": f"<b>{label}</b><br>comments shown: {s:.1f}% caught"})
        facts["gap_" + ("b" if col == "bare" else "c")] = s - r
        rows.append({"cutoff": label, "caught_comments_removed": round(r, 2),
                     "caught_comments_shown": round(s, 2), "gap_points": round(s - r, 2)})

    gaps = [f"{label}\nshowing comments catches {row['gap_points']:.0f} points more"
            for (_, label), row in zip(CUTOFFS, rows)]
    dot = {"type": "scatter", "symbolSize": 16, "z": 3,
           "label": {"show": True, "fontSize": 12, "fontWeight": 600, "color": "@ink-primary", "distance": 10}}
    option = C.base(
        grid={"left": 16, "right": 70, "top": 8, "bottom": 52, "containLabel": True},
        xAxis=C.axis("Backdoors caught", type="value", min=70, max=100, axisLabel={"formatter": "{value}%"}),
        yAxis={"type": "category", "inverse": True, "data": gaps, "axisTick": {"show": False},
               "axisLine": {"show": False},
               "axisLabel": {"margin": 14, "align": "right",
                             "formatter": "function (v) { var p = v.split('\\n'); return '{a|' + p[0] + '}\\n{b|' + p[1] + '}'; }",
                             "rich": {"a": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 600,
                                            "lineHeight": 20, "align": "right"},
                                      "b": {"color": "@ink-muted", "fontSize": 11, "lineHeight": 16, "align": "right"}}}},
        series=links + [
            {**dot, "name": "Comments removed", "data": removed,
             "itemStyle": {"color": "@context-strong", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "label": {**dot["label"], "position": "left"}},
            {**dot, "name": "Comments shown", "data": shown,
             "itemStyle": {"color": "@s0", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "label": {**dot["label"], "position": "right"}},
        ],
    )
    return Figure(option=option, data=rows, facts=facts)
