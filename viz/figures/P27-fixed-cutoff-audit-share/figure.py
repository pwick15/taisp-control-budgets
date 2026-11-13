"""P27: why you can't pick a suspicion cutoff by feel. The same cutoff score audits wildly different shares
of clean code depending on the monitor, which is why the study sets each monitor's cutoff on clean code.

One configuration per model, at its default reasoning effort, on the 0 to 10 scale with comments removed.
"""
import numpy as np

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P27",
    "title": "The same score cutoff audits {lo:.1f}% to {hi:.0f}% of clean code",
    "section": "setup",
    "order": 25,
    "caption": ("Share of our 500 clean programs each monitor would send to a human if you audited every program "
                "scoring 5 or more out of 10. The dashed line is a 2% budget, and the axis is on a log scale. The "
                "dial changes the cutoff score."),
    "notes": [
        "One configuration per model, at its default reasoning effort, 0 to 10 scale, comments removed. One clean "
        "program is 0.2% of 500, so 0.2% means a single program.",
        "At a cutoff of 5, {n_under} monitors audit under 2% and {n_over} audit over it. At a cutoff of 1 the range "
        "is {lo1:.1f}% to {hi1:.0f}%.",
        "Setting each monitor's cutoff on clean code instead (P25) puts every monitor on the dashed line by "
        "construction, which is what the study does.",
    ],
    "height": 520,
}

DEFAULT = {"sonnet55": "high", "haiku55": "medium", "haiku45": "off", "glm53": "max", "qwen38": "medium",
           "luna": "medium", "gptoss": "medium", "gemma4": "default", "gemini35lite": "off", "gemma3": "default",
           "gemma3_27b": "default", "mistrallarge4": "default", "ministral14b": "default"}
CUTS = (1, 3, 5, 7)
BUDGET = 2
X_MIN, X_MAX = 0.1, 100

# A horizontal bar from the left edge of the log axis to the value. ECharts' own bars on a log axis grow
# from 1, which would draw every share under 1% leftwards. value: [share, row].
BAR = ("function (params, api) { var a = api.coord([%s, api.value(1)]); var b = api.coord([api.value(0), api.value(1)]);"
       " var h = 16; return {type: 'rect', shape: {x: a[0], y: a[1] - h / 2, width: Math.max(b[0] - a[0], 2),"
       " height: h, r: [0, 4, 4, 0]}, style: api.style()}; }" % X_MIN)


def build() -> Figure:
    runs = {m: r for r, (_, m, _, e) in S.RUNS.items() if r not in S.EXCLUDE and DEFAULT.get(m) == e}
    share = {}
    for m, run in runs.items():
        h, _ = S.load_scores(run)
        v = np.round(h.values * 10)
        share[m] = {c: 100 * float((v >= c).mean()) for c in CUTS}
    order = sorted(share, key=lambda m: share[m][5], reverse=True)
    names = [S.MODEL_NAMES[m] for m in order]

    def frame(c):
        data = []
        for i, m in enumerate(order):
            v = max(share[m][c], X_MIN)
            over = v > BUDGET
            n = round(share[m][c] * 5)
            data.append({"value": [round(v, 2), i],
                         "itemStyle": {"color": "@s7" if over else "@s0"},
                         "label": {"formatter": f"{share[m][c]:.1f}%"},
                         "tip": f"<b>{S.MODEL_NAMES[m]}</b><br>{n} of 500 clean programs score {c} or more"
                                f" ({share[m][c]:.1f}%)"})
        return {"series": [
            {"name": "_bars", "type": "custom", "renderItem": BAR, "data": data, "encode": {"x": 0, "y": 1},
             "label": {"show": True, "position": "right", "distance": 6, "color": "@ink-secondary", "fontSize": 11},
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"type": "dashed", "color": "@ink-primary", "width": 1.5},
                          "label": {"formatter": f"{BUDGET}% budget", "position": "end", "color": "@ink-secondary",
                                    "fontSize": 11},
                          "data": [{"xAxis": BUDGET}]}},
            {"name": "Over budget", "type": "bar", "data": [], "itemStyle": {"color": "@s7"}},
            {"name": "At or under budget", "type": "bar", "data": [], "itemStyle": {"color": "@s0"}},
        ]}

    frames = [frame(c) for c in CUTS]
    option = C.base(
        grid={"left": 16, "right": 56, "top": 40, "bottom": 46, "containLabel": True},
        legend={"top": 0, "left": 0, "data": ["At or under budget", "Over budget"], "selectedMode": False},
        xAxis=C.axis("Clean programs audited (log scale)", gap=30, type="log", min=X_MIN, max=X_MAX, logBase=10,
                     axisLabel={"formatter": "{value}%"}),
        yAxis={"type": "category", "data": names, "inverse": True, "axisLine": {"show": False},
               "axisTick": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500}},
        series=frames[CUTS.index(5)]["series"],
    )
    at5 = [share[m][5] for m in order]
    at1 = [share[m][1] for m in order]
    data = [{"monitor": S.MODEL_NAMES[m], "run": runs[m], **{f"pct_at_{c}_or_more": share[m][c] for c in CUTS}}
            for m in order]
    return Figure(option=option, data=data,
                  facts={"lo": min(at5), "hi": max(at5), "n_under": sum(v < BUDGET for v in at5),
                         "n_over": sum(v > BUDGET for v in at5), "lo1": min(at1), "hi1": max(at1)},
                  dial={"label": "Audit scores of", "steps": [f"{c} or more" for c in CUTS],
                        "initial": CUTS.index(5), "frames": frames})
