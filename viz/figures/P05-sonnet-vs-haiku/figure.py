"""P05: Sonnet 5.5 against Haiku 5.5 xhigh across audit budgets, with Sonnet's paired lead below."""
from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P05",
    "title": "Haiku at xhigh keeps up with Sonnet from 2% up, not below",
    "section": "results",
    "order": 50,
    "caption": ("Top: share of backdoors caught as the audit budget grows, with 95% bands; Haiku at its default "
                "is there for reference. Bottom: Sonnet's lead over Haiku xhigh. Its band comes from a paired "
                "bootstrap, so it is tighter than comparing the top bands by eye."),
    "notes": [
        "This changes the web/ summary page, which says the two can't be separated because their intervals "
        "overlap. With exact budgets and a paired test the gap is small but above zero at every budget, and "
        "Marnick's matched-rate test agrees.",
        "Method, as agreed: Marnick's matched-rate number for the tight-budget claim, this exact-budget curve "
        "for the overview. Check the gap is quoted the way results/analysis/MONITOR-GAP.md means it.",
        "Below 1% the cutoff rests on 5 honest programs or fewer, so the bands are wide. The gap there is real "
        "but its size is not well measured.",
    ],
    "height": 600,
}

FINE = (0.2, 0.3, 0.5, 0.75, 1, 1.5, 2, 3, 5, 7.5, 10, 15, 20)
RUNS = [(S.SONNET, "Sonnet 5.5", entity("sonnet55"), True), (S.HAIKU_X, "Haiku 5.5 · xhigh", entity("haiku55"), True),
        (S.HAIKU_DEFAULT, "Haiku 5.5 · default", "@context-strong", False)]
LEAD = "Sonnet's lead"


def build() -> Figure:
    series, rows = [], []
    for run, name, color, band in RUNS:
        pts = S.curve(run, FINE)
        series.append({
            "name": name, "type": "line", "xAxisIndex": 0, "yAxisIndex": 0, "symbolSize": 6,
            "itemStyle": {"color": color}, "lineStyle": {"color": color, "width": 2 if band else 1.5},
            "data": [{"value": [p["b"], round(100 * p["v"], 2)],
                      "tip": f"<b>{name}</b><br>{p['b']:g}% budget: {C.pct(p['v'])}% ({C.pct(p['lo'])} to {C.pct(p['hi'])})"}
                     for p in pts],
        })
        if band:
            series.append({"name": name, "type": "custom", "renderItem": C.BAND, "xAxisIndex": 0, "yAxisIndex": 0,
                           "clip": True, "itemStyle": {"color": color}, "data": C.band_data(pts),
                           "encode": {"x": [0, 3], "y": [1, 2, 4, 5]}, "silent": True, "tooltip": {"show": False}})
        rows += [{"series": name, "budget_pct": p["b"], "value": p["v"], "lo": p["lo"], "hi": p["hi"]} for p in pts]
    diff = S.paired_diff(S.SONNET, S.HAIKU_X, FINE)
    dp = [{"b": r.budget_pct, "v": r["diff"], "lo": r.lo, "hi": r.hi} for _, r in diff.iterrows()]
    rows += [{"series": LEAD, "budget_pct": p["b"], "value": p["v"], "lo": p["lo"], "hi": p["hi"]} for p in dp]
    series.append({
        "name": LEAD, "type": "line", "xAxisIndex": 1, "yAxisIndex": 1, "symbolSize": 6,
        "itemStyle": {"color": "@s6"}, "lineStyle": {"color": "@s6", "width": 2},
        "data": [{"value": [p["b"], round(100 * p["v"], 2)],
                  "tip": f"<b>{LEAD}</b><br>{p['b']:g}% budget: {100 * p['v']:+.1f} points "
                         f"({100 * p['lo']:+.1f} to {100 * p['hi']:+.1f})"} for p in dp],
        "markLine": {"silent": True, "symbol": "none", "lineStyle": {"color": "@ink-muted", "type": "dashed"},
                     "label": {"show": False}, "data": [{"yAxis": 0}]},
    })
    series.append({"name": LEAD, "type": "custom", "renderItem": C.BAND, "xAxisIndex": 1, "yAxisIndex": 1, "clip": True,
                   "itemStyle": {"color": "@s6"}, "data": C.band_data(dp),
                   "encode": {"x": [0, 3], "y": [1, 2, 4, 5]}, "silent": True, "tooltip": {"show": False}})
    xa = {"type": "log", "min": 0.2, "max": 20, "axisLabel": {"formatter": "{value}%"}}
    option = C.base(
        grid=[{"left": 58, "right": 24, "top": 44, "height": "47%"},
              {"left": 58, "right": 24, "bottom": 52, "height": "22%"}],
        xAxis=[C.axis("", **{**xa, "axisLabel": {"show": False}}),
               C.axis("Audit budget (log scale)", gridIndex=1, **xa)],
        yAxis=[C.axis("Backdoors caught", gap=44, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
               C.axis("Lead (points)", gap=44, type="value", gridIndex=1, min=-10)],
        legend={"top": 0, "left": 50, "data": [r[1] for r in RUNS] + [LEAD]},
        series=series,
    )
    return Figure(option=option, data=rows)
