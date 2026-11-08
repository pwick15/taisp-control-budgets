"""A05: each lab incident as a line from when it happened to when it became public, coloured by lab."""
from datetime import date, timedelta
from statistics import median

from viz.data import incidents as I
from viz.kit import Figure
from viz.lib import charts as C

META = {
    "id": "A05",
    "title": "Lab incidents surfaced months after they happened",
    "section": "intro",
    "order": 40,
    "caption": ("Each line is one of {n} lab incidents, running from when it happened (open circle) to when it "
                "became public (filled). Dashed lines mark the median dates; half took {median:.0f} days or more "
                "to surface."),
    "notes": [
        "Only lab and evaluator incidents with a usable incident date are shown, the same set as A02. A date "
        "known only to the month is placed mid-month.",
        "Grey covers incidents involving other or several labs: the UK AISI test (Anthropic and OpenAI models) "
        "and the Tencent Cloud fleet. Data: the A01 incident log.",
    ],
}

COLOURS = {"OpenAI": "@s6", "Anthropic": "@s1", "Google": "@s0", "Other": "@context-strong"}


def mid_date(dates: list[str]) -> str:
    ds = sorted(date.fromisoformat(d) for d in dates)
    n = len(ds)
    m = ds[n // 2] if n % 2 else ds[n // 2 - 1] + (ds[n // 2] - ds[n // 2 - 1]) / 2
    return m.isoformat()


def build() -> Figure:
    rows = I.lab_timeline()
    labels = [r["company"] for r in rows]
    series = []
    for group in I.COMPANIES:
        col = COLOURS[group]
        mine = [(i, r) for i, r in enumerate(rows) if I.colour_group(r["company"]) == group]
        if not mine:
            continue
        tip = lambda r: (f"<b>{r['short']}</b><br>{r['company']}<br>happened {'~' if r['approx'] else ''}{r['occurred']}"
                         f"<br>public {r['public']} ({'about ' if r['approx'] else ''}{r['days']} days)")
        series.append({"type": "lines", "name": group, "coordinateSystem": "cartesian2d", "z": 2, "silent": True,
                       "lineStyle": {"color": col, "width": 3, "opacity": 0.45},
                       "data": [{"coords": [[r["occurred"], i], [r["public"], i]]} for i, r in mine]})
        series.append({"type": "scatter", "name": group, "z": 3, "symbolSize": 10,
                       "itemStyle": {"color": "@ink-surface", "borderColor": col, "borderWidth": 2},
                       "data": [{"value": [r["occurred"], i], "tip": tip(r)} for i, r in mine]})
        series.append({"type": "scatter", "name": group, "z": 4, "symbolSize": 11,
                       "itemStyle": {"color": col},
                       "data": [{"value": [r["public"], i], "tip": tip(r)} for i, r in mine]})
    med_occ, med_pub = mid_date([r["occurred"] for r in rows]), mid_date([r["public"] for r in rows])
    series.append({"type": "scatter", "name": "median", "data": [], "silent": True,
                   "markLine": {"silent": True, "symbol": "none",
                                "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1},
                                "label": {"position": "start", "color": "@ink-secondary", "fontSize": 12},
                                "data": [{"xAxis": med_occ, "label": {"formatter": "Median incident"}},
                                         {"xAxis": med_pub, "label": {"formatter": "Median disclosure"}}]}})
    start = (date.fromisoformat(min(r["occurred"] for r in rows)).replace(day=1)).isoformat()
    end = (date.fromisoformat(max(r["public"] for r in rows)).replace(day=1) + timedelta(days=45)).replace(day=1).isoformat()
    option = C.base(
        grid={"left": 170, "right": 28, "top": 44, "bottom": 36},
        legend={"top": 0, "left": 170, "data": [g for g in I.COMPANIES if any(I.colour_group(r["company"]) == g for r in rows)]},
        xAxis={"type": "time", "min": start, "max": end, "splitLine": {"show": True, "lineStyle": {"color": "@ink-grid"}},
               "axisLabel": {"formatter": "{MMM} {yyyy}", "hideOverlap": True}},
        yAxis={"type": "category", "inverse": True, "data": labels, "axisLine": {"show": False}, "axisTick": {"show": False},
               "splitLine": {"show": False}, "axisLabel": {"color": "@ink-primary", "fontSize": 12, "interval": 0}},
        series=series,
    )
    data = [{"incident": r["short"], "lab": r["company"], "happened": r["occurred"], "date_known_to_month_only": r["approx"],
             "became_public": r["public"], "days": r["days"]} for r in rows]
    return Figure(option=option, height=110 + 26 * len(rows), data=data,
                  facts={"n": len(rows), "median": median(r["days"] for r in rows)})
