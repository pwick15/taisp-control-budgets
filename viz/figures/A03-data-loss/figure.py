"""A03: data individuals say an AI agent destroyed (the incident page's loss chart)."""
from viz.data import incidents as I
from viz.kit import Figure
from viz.lib import charts as C

META = {
    "id": "A03",
    "title": "Single agent mistakes cost individuals up to {top:,.0f} GB of data",
    "section": "intro",
    "order": 20,
    "caption": ("Reported data loss in the {n} first-person reports that give a size, {total:,.0f} GB in all. "
                "Each bar is one person's report."),
    "notes": [
        "Sizes are the reporters' own and have not been independently verified. Recovery varied, and some "
        "reports involved safety settings turned off.",
        "One-off reports don't show how often this happens or allow vendor comparisons. Data: the A01 incident log.",
    ],
}


def build() -> Figure:
    rows = I.loss()
    bars = [{"value": r["gb"], "label": {"formatter": f"{r['gb']:,.0f} GB"},
             "tip": f"{r['when']}<br><b>{r['actor']}</b>: {r['gb']:,.0f} GB<br>Recovery: {r['recovery'] or 'not stated'}"}
            for r in rows]
    option = C.base(
        grid={"left": 210, "right": 72, "top": 8, "bottom": 28},
        xAxis={"type": "value", "axisLabel": {"formatter": "{value} GB"}},
        yAxis={"type": "category", "inverse": True, "data": [r["short"] for r in rows],
               "axisLine": {"show": False}, "splitLine": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 12, "interval": 0}},
        series=[{
            "type": "bar", "data": bars, "barWidth": 16,
            "itemStyle": {"color": "@s2", "borderRadius": [0, 4, 4, 0]},
            "label": {"show": True, "position": "right", "color": "@ink-secondary", "fontSize": 12},
        }],
    )
    data = [{"report": r["short"], "who": r["actor"], "when": r["when"], "gb": r["gb"], "recovery": r["recovery"]}
            for r in rows]
    return Figure(option=option, height=70 + 30 * len(rows), data=data,
                  facts={"top": rows[0]["gb"], "total": sum(r["gb"] for r in rows), "n": len(rows)})
