"""A02: days from each lab incident to its first public report (the incident page's lag chart)."""
from statistics import median

from viz.data import incidents as I
from viz.kit import Figure
from viz.lib import charts as C

# Shorter chart labels, so the chart stays inside the style guide's word budget. The page keeps the long ones.
LABELS = {"UK AISI test: backdoor attempt": "UK AISI backdoor test",
          "Grader model files fraudulent reports": "Grader files fraudulent reports"}

META = {
    "id": "A02",
    "title": "Lab incidents typically took {median:.0f} days to become public",
    "section": "intro",
    "order": 10,
    "caption": ("Days from each incident to its first public report, for the {n} lab incidents with a usable date. "
                "A ~ marks an incident date known only to the month, measured from mid-month. "
                "The dashed line is the median."),
    "notes": [
        "Incidents with no published date, or spanning several months, are left out. Data: the A01 incident log.",
    ],
}


def build() -> Figure:
    rows = I.lag()
    med = median(r["days"] for r in rows)
    bars = [{"value": r["days"], "label": {"formatter": ("~" if r["approx"] else "") + f"{r['days']:,}"},
             "tip": f"{r['when']}<br><b>{r['short']}</b>: {'about ' if r['approx'] else ''}{r['days']:,} days"}
            for r in rows]
    option = C.base(
        grid={"left": 270, "right": 56, "top": 28, "bottom": 28},
        xAxis={"type": "value"},
        yAxis={"type": "category", "inverse": True, "data": [LABELS.get(r["short"], r["short"]) for r in rows],
               "axisLine": {"show": False}, "splitLine": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 12, "interval": 0}},
        series=[{
            "type": "bar", "data": bars, "barWidth": 14,
            "itemStyle": {"color": "@s0", "borderRadius": [0, 4, 4, 0]},
            "label": {"show": True, "position": "right", "color": "@ink-secondary", "fontSize": 12},
            "markLine": {"silent": True, "symbol": "none",
                         "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1},
                         "label": {"position": "start", "formatter": "Median",
                                   "color": "@ink-secondary", "fontSize": 12},
                         "data": [{"xAxis": med}]},
        }],
    )
    data = [{"incident": r["short"], "when": r["when"], "date_known_to_month_only": r["approx"], "days": r["days"]}
            for r in rows]
    return Figure(option=option, height=70 + 26 * len(rows), data=data, facts={"median": med, "n": len(rows)})
