"""Chart pieces shared by figures. Content and tokens only: the gallery's theme supplies fonts,
axis colours, gridlines and tooltip styling, so don't restate them here or in a figure.
"""
from __future__ import annotations

from viz.lib.safety import wilson

# Tooltip: a data item's own "tip" (HTML) if it has one, else the series name.
TIP = "function (p) { return (p.data && p.data.tip) ? p.data.tip : p.seriesName; }"

# A 95% interval drawn as a soft vertical bar behind a marker. Data: [x, lo, hi].
VBAR = ("function (params, api) { var a = api.coord([api.value(0), api.value(1)]);"
        " var b = api.coord([api.value(0), api.value(2)]);"
        " return {type: 'line', shape: {x1: a[0], y1: a[1], x2: b[0], y2: b[1]},"
        " style: {stroke: api.visual('color'), lineWidth: 7, lineCap: 'round', opacity: 0.2}, silent: true}; }")


# A shaded band between two points' intervals. Data: [x1, lo1, hi1, x2, lo2, hi2].
BAND = ("function (params, api) { var p1 = api.coord([api.value(0), api.value(1)]);"
        " var p2 = api.coord([api.value(0), api.value(2)]); var p3 = api.coord([api.value(3), api.value(5)]);"
        " var p4 = api.coord([api.value(3), api.value(4)]);"
        " return {type: 'polygon', shape: {points: [p1, p4, p3, p2]},"
        " style: {fill: api.visual('color'), opacity: 0.15}, silent: true}; }")

# A horizontal block from x0 to x1 on category row y. Data: [x0, x1, row].
BLOCK = ("function (params, api) { var a = api.coord([api.value(0), api.value(2)]);"
         " var b = api.coord([api.value(1), api.value(2)]); var h = api.size([0, 1])[1] * 0.6;"
         " return {type: 'rect', shape: {x: a[0], y: a[1] - h / 2, width: Math.max(b[0] - a[0], 1), height: h, r: 2},"
         " style: api.style()}; }")


def band_data(points: list[dict], scale: float = 100) -> list:
    """BAND data from points [{"b", "lo", "hi"}, ...] sorted by b."""
    return [[p["b"], round(scale * p["lo"], 2), round(scale * p["hi"], 2),
             q["b"], round(scale * q["lo"], 2), round(scale * q["hi"], 2)] for p, q in zip(points, points[1:])]


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}"


def money(x: float) -> str:
    return f"${x:.4f}" if x >= 0.001 else f"${x:.5f}"


def axis(name: str = "", gap: int = 34, **kw) -> dict:
    """An axis with its name centred along it. Style comes from the theme."""
    out = {"name": name, "nameLocation": "middle", "nameGap": gap}
    out.update(kw)
    return out


def base(**kw) -> dict:
    out = {"tooltip": {"trigger": "item", "formatter": TIP, "confine": True}, "animation": False}
    out.update(kw)
    return out


def heat_table(cols: list[str], rows: list[str], cells: list[dict], left: int = 140, cell_h: int = 64) -> dict:
    """A table drawn as coloured cells, each carrying its number.

    cells: {"col": i, "row": j, "color": token, "text": "87.6%"}. Use a scale token such as
    "@goodbad:0.8" or "@seq:0.4" so the cell works in light and dark mode; the number is always
    printed, so colour never carries the value alone. For a second, smaller line write
    "{big|87.6%}\\n{small|best of the three}".
    """
    data = [{"value": [c["col"], c["row"], 1], "itemStyle": {"color": c["color"]},
             "label": {"formatter": c["text"]}} for c in cells]
    return {
        "option": base(
            tooltip={"show": False},
            grid={"left": left, "right": 16, "top": 40, "bottom": 12},
            xAxis={"type": "category", "data": cols, "position": "top", "axisLine": {"show": False},
                   "axisLabel": {"color": "@ink-secondary", "fontSize": 12, "fontWeight": 600, "interval": 0}},
            yAxis={"type": "category", "data": rows, "inverse": True, "axisLine": {"show": False},
                   "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500, "margin": 16}},
            series=[{"type": "heatmap", "data": data, "silent": True,
                     "itemStyle": {"borderColor": "@ink-surface", "borderWidth": 3, "borderRadius": 8},
                     "label": {"show": True, "color": "@on-pale", "fontSize": 18, "fontWeight": 600, "align": "center",
                               "rich": {"big": {"color": "@on-pale", "fontSize": 18, "fontWeight": 600, "lineHeight": 26,
                                                "align": "center"},
                                        "small": {"color": "@on-pale", "fontSize": 12, "lineHeight": 16, "align": "center"}}}}],
        ),
        "height": 40 + 12 + cell_h * len(rows),
    }


def partition_bars(rows: list[tuple[str, int, list[int]]], parts: list[tuple[str, str, str]],
                   x_name: str, range_head: str) -> dict:
    """100% bars, one per row, with the 95% range of the first part's share on the right.

    rows:  (label, n, counts per part)
    parts: (legend name, fill token, label-text token)
    """
    series = []
    for p, (name, fill, ink) in enumerate(parts):
        data = []
        for label, n, counts in rows:
            k = int(counts[p])
            v = 100 * k / n
            nz = [i for i, c in enumerate(counts) if c > 0]
            radius = [6 if p == nz[0] else 0, 6 if p == nz[-1] else 0, 6 if p == nz[-1] else 0, 6 if p == nz[0] else 0]
            data.append({
                "value": round(v, 2),
                "itemStyle": {"borderRadius": radius},
                "label": {"show": v >= 8, "formatter": f"{v:.0f}%", "color": ink},
                "tip": f"<b>{label}</b> (n = {n})<br>{name.lower()}: {k} ({v:.0f}%)",
            })
        series.append({"name": name, "type": "bar", "stack": "all", "data": data, "barWidth": 22,
                       "itemStyle": {"color": fill, "borderColor": "@ink-surface", "borderWidth": 2},
                       "label": {"fontSize": 12, "fontWeight": 600}})
    ranges = []
    for i, (label, n, counts) in enumerate(rows):
        lo, hi = wilson(int(counts[0]), int(n))
        ranges.append({"value": [100, i], "name": f"{100 * lo:.0f}–{100 * hi:.0f}%"})
    series.append({"name": "_range", "type": "scatter", "symbolSize": 0, "data": ranges, "silent": True,
                   "clip": False, "tooltip": {"show": False},
                   "label": {"show": True, "position": "right", "distance": 18, "formatter": "{b}",
                             "color": "@ink-secondary", "fontSize": 12}})
    # Category text is exactly what's drawn, so containLabel measures the real width.
    cats = [f"{label}  n = {n}" for label, n, _ in rows]
    return base(
        grid={"left": 24, "right": 92, "top": 52, "bottom": 46, "containLabel": True},
        legend={"top": 0, "left": 0, "data": [p[0] for p in parts], "selectedMode": False},
        graphic=[{"type": "text", "right": 12, "top": 30,
                  "style": {"text": range_head, "fill": "@ink-muted", "fontSize": 11, "align": "right"}}],
        xAxis=axis(x_name, gap=30, type="value", min=0, max=100, interval=25,
                   axisLabel={"formatter": "{value}%"}),
        yAxis={"type": "category", "data": cats, "inverse": True, "axisLine": {"show": False},
               "axisLabel": {"fontSize": 13, "fontWeight": 500,
                             "formatter": "function (v) { var p = v.split('  n = '); return '{n|' + p[0] + '}  {c|n = ' + p[1] + '}'; }",
                             "rich": {"n": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500},
                                      "c": {"color": "@ink-muted", "fontSize": 12}}}},
        series=series,
    )


def score_histograms(runs: list[tuple[str, str]], step: float, scale_label: str) -> tuple[dict, list, dict]:
    """Honest vs backdoored score counts, one panel per monitor, on a 0 to 1 axis so 0 to 10 and
    0 to 100 runs line up. Returns (option, data rows, facts: share of honest programs on the top score)."""
    from viz.lib.safety import load_scores, safety_at
    grids, xs, ys, series, graphic, rows, facts = [], [], [], [], [], [], {}
    bar_w = 9 if step >= 0.1 else 3
    for i, (run, name) in enumerate(runs):
        h, a = load_scores(run)
        s = safety_at(h.values, a.values, 0.02)
        left = 6 + i * 50
        grids.append({"left": f"{left + 3}%", "width": "39%", "top": 56, "bottom": 70})
        graphic.append({"type": "text", "left": f"{left + 3}%", "top": 26,
                        "style": {"text": name, "fill": "@ink-primary", "fontSize": 13, "fontWeight": 600}})
        xs.append(axis(f"Suspicion score ({scale_label}, as 0 to 1)", gridIndex=i, type="value", min=-0.03, max=1.03,
                       splitLine={"show": False}))
        ys.append(axis("Programs (log scale)" if i == 0 else "", gap=44, gridIndex=i, type="log", min=0.5, max=1000,
                       axisLabel={"formatter": "function (v) { return v < 1 ? '' : String(v); }"}))
        hc, ac = h.round(2).value_counts(), a.round(2).value_counts()
        for mode, counts, color, off in (("honest", hc, "@context-strong", -step / 6), ("backdoored", ac, "@s7", step / 6)):
            off = off if step >= 0.1 else 0
            series.append({
                "name": f"{mode} programs", "type": "bar", "xAxisIndex": i, "yAxisIndex": i, "barWidth": bar_w,
                "barGap": "-100%" if step < 0.1 else "10%", "itemStyle": {"color": color, "borderRadius": [2, 2, 0, 0]},
                "z": 3 if mode == "honest" else 2,
                "data": [{"value": [round(v + off, 4), int(c)],
                          "tip": f"<b>{name}</b><br>{int(c)} {mode} programs scored {v:.2f}"} for v, c in counts.items()],
                **({"markArea": {"silent": True, "itemStyle": {"color": "@s2/0.1"},
                                 "label": {"show": True, "position": "insideTop", "color": "@ink-secondary", "fontSize": 11,
                                           "formatter": f"audited at 2%\n(really {100 * s['served']:.1f}%)"},
                                 "data": [[{"xAxis": round(s["cutoff"] + step / 2, 4)}, {"xAxis": 1.03}]]}}
                   if mode == "honest" else {}),
            })
            rows += [{"monitor": name, "programs": mode, "score": float(v), "count": int(c)} for v, c in counts.items()]
        top = h.round(2).value_counts()
        facts[f"top{i}"] = 100 * top.iloc[0] / len(h)
        facts[f"distinct{i}"] = int(h.nunique())
    option = base(grid=grids, xAxis=xs, yAxis=ys, series=series, graphic=graphic,
                  legend={"top": 0, "left": "6%", "data": ["honest programs", "backdoored programs"]})
    return option, rows, facts
