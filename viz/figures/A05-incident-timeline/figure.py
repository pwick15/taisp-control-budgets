"""A05: every incident as a dot, stacked by month, with a dial to switch between when it happened
and when it became public (the incident page's timeline). Its dial makes it a GIF in the gallery."""
from datetime import date

from viz.data import incidents as I
from viz.kit import Figure
from viz.lib import charts as C

META = {
    "id": "A05",
    "title": "Lab incidents surfaced months after they happened",
    "section": "intro",
    "order": 40,
    "caption": ("Each dot is one of {n} incidents, stacked by month. Switch the dial to move each dot from when it "
                "happened to when it became public. Filled dots are confirmed by the operator or affected party, "
                "hollow ones attributed or disputed, dotted ones self-reported."),
    "notes": [
        "{undated} incidents have no published incident date, so they only appear in the 'became public' view.",
        "Data: the A01 incident log. Lane colours match A01 (labs blue, companies orange, individuals aqua).",
    ],
    "height": 520,
}

COLOURS = ["@s0", "@s1", "@s2"]
PITCH = 15          # px between stacked dots
SIZE = 11           # dot diameter
TOP, LANE_HEAD, LANE_GAP, BOTTOM = 8, 26, 14, 30


def month_label(m: str) -> str:
    return date.fromisoformat(m + "-01").strftime("%b %Y")


def build() -> Figure:
    rows = sorted(I.incidents(), key=lambda r: r["id"])
    months = I.months()
    views = {"occurred": I.stack("occurred"), "public": I.stack("public")}
    lane_max = [max([k + 1 for v in views.values() for (l, _, k) in v.values() if l == li] or [1])
                for li in range(len(I.LANES))]

    grids, xs, ys, graphic, y = [], [], [], [], TOP
    for li, name in enumerate(I.LANES):
        h = lane_max[li] * PITCH
        graphic.append({"type": "text", "left": 40, "top": y, "silent": True,
                        "style": {"text": name, "fill": "@ink-primary", "fontSize": 12, "fontWeight": 600}})
        grids.append({"left": 40, "right": 24, "top": y + LANE_HEAD, "height": h})
        last = li == len(I.LANES) - 1
        xs.append({"type": "category", "gridIndex": li, "data": [month_label(m) for m in months],
                   "boundaryGap": True, "axisLine": {"show": True}, "splitLine": {"show": False},
                   "axisLabel": {"show": last, "interval": 2}})
        ys.append({"type": "value", "gridIndex": li, "min": 0, "max": lane_max[li], "show": False})
        y += LANE_HEAD + h + LANE_GAP
    height = y - LANE_GAP + BOTTOM

    def series(view: str) -> list[dict]:
        out = []
        for li, lane in enumerate(I.LANES):
            data = []
            for r in (r for r in rows if r["lane"] == lane):
                pos = views[view].get(r["id"])
                shown = pos is not None
                _, m, k = pos if shown else views["public"].get(r["id"], (li, 0, 0))
                ev = r["evidence"]
                data.append({
                    "value": [m, k + 0.5], "name": r["short"],
                    "tip": f"{r['when']}<br><b>{r['short']}</b><br>{ev}",
                    "itemStyle": {"color": COLOURS[li] if ev == "Confirmed" else "@ink-surface",
                                  "borderColor": COLOURS[li], "borderWidth": 2,
                                  "borderType": "dotted" if ev == "Self-reported" else "solid",
                                  "opacity": 1 if shown else 0}})
            out.append({"type": "scatter", "id": f"lane{li}", "xAxisIndex": li, "yAxisIndex": li,
                        "symbolSize": SIZE, "data": data})
        return out

    option = C.base(grid=grids, xAxis=xs, yAxis=ys, graphic=graphic, series=series("occurred"))
    option["animation"] = True
    option["animationDurationUpdate"] = 700
    option["animationEasingUpdate"] = "cubicOut"
    dial = {"label": "Date shown", "steps": ["When it happened", "When it became public"], "initial": 0,
            "frames": [{"series": series("occurred")}, {"series": series("public")}]}
    data = [{"incident": r["short"], "lane": r["lane"], "evidence": r["evidence"],
             "occurred": r.get("occurred"), "public": r.get("public")} for r in rows]
    undated = sum(1 for r in rows if not r.get("occurred"))
    return Figure(option=option, dial=dial, height=height, data=data, facts={"n": len(rows), "undated": undated})
