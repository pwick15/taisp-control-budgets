"""P04: median reasoning tokens per program at each effort setting, with the jump between settings."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P04",
    "title": "The same effort setting means very different amounts of thinking",
    "section": "results",
    "order": 40,
    "caption": ("Median reasoning tokens per program at each effort setting we ran. The number between two "
                "cells is the change from one setting to the next; red means it went down. Empty cells are "
                "settings we didn't run."),
    "notes": [
        "Sonnet 5.5 and Mistral Large 4 report no reasoning tokens in their usage, so their cells say not logged. "
        "It doesn't mean they didn't think.",
    ],
    "height": 470,
}

EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
LADDER = {"haiku55": "Haiku 5.5", "glm53": "GLM-5.3", "gptoss": "gpt-oss-120b", "qwen38": "Qwen 3.8 Omni Flash",
          "gemini35lite": "Gemini 3.5 Flash-Lite", "luna": "GPT-6 Luna", "sonnet55": "Sonnet 5.5",
          "mistrallarge4": "Mistral Large 4"}

# A rounded cell with its number. value: [column, row, tokens]; tokens < 0 means not logged.
CELL = ("function (params, api) { var c = api.coord([api.value(0), api.value(1)]);"
        " var w = api.size([1, 0])[0] * 0.62, h = api.size([0, 1])[1] * 0.66; var v = api.value(2);"
        " var t = v < 0 ? 'not logged' : String(Math.round(v)).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');"
        " return {type: 'group', children: [{type: 'rect', shape: {x: c[0] - w / 2, y: c[1] - h / 2, width: w, height: h, r: 7},"
        " style: api.style()}, {type: 'text', silent: true, style: {text: t, x: c[0], y: c[1], align: 'center',"
        " verticalAlign: 'middle', fontSize: v < 0 ? 12 : 15, fontWeight: v < 0 ? 'normal' : 600,"
        " fill: v < 0 ? '@ink-muted' : '@on-pale'}}]}; }")

# The change between two cells, written above a thin connector. value: [from col, to col, row, delta].
JUMP = ("function (params, api) { var a = api.coord([api.value(0), api.value(2)]);"
        " var b = api.coord([api.value(1), api.value(2)]); var w = api.size([1, 0])[0] * 0.31;"
        " var x1 = a[0] + w, x2 = b[0] - w, d = api.value(3); var s = (d >= 0 ? '+' : '−') +"
        " String(Math.abs(Math.round(d))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');"
        " return {type: 'group', children: [{type: 'line', shape: {x1: x1 + 3, y1: a[1] + 9, x2: x2 - 3, y2: a[1] + 9},"
        " style: {stroke: api.visual('color'), lineWidth: 1.2}},"
        " {type: 'text', silent: true, style: {text: s, x: (x1 + x2) / 2, y: a[1] - 2, align: 'center',"
        " verticalAlign: 'bottom', fontSize: 12, fontWeight: 600, fill: api.visual('color')}}]}; }")


def build() -> Figure:
    t = S.run_table()
    runs = t.drop_duplicates("run")
    cells, jumps, rows = [], [], []
    for i, (model, label) in enumerate(LADDER.items()):
        by = {}
        for _, r in runs[runs.model == model].iterrows():
            by[EFFORT_ORDER.index(REMAP.get(r.effort, r.effort))] = S.median_reasoning(r.run)
            rows.append({"model": label, "effort": r.effort, "run": r.run, "median_reasoning_tokens": by[EFFORT_ORDER.index(REMAP.get(r.effort, r.effort))]})
        logged = any(v > 0 for v in by.values())
        cols = sorted(by)
        for c in cols:
            v = by[c] if logged else -1
            cells.append({"value": [c, i, v], "itemStyle": {"color": "@seq:0.5" if v > 0 else "@mid"}})
        if logged:
            for a, b in zip(cols, cols[1:]):
                d = by[b] - by[a]
                jumps.append({"value": [a, b, i, d], "itemStyle": {"color": "@ink-secondary" if d >= 0 else "@s7"}})
    option = C.base(
        tooltip={"show": False},
        grid={"left": 170, "right": 20, "top": 40, "bottom": 10},
        xAxis={"type": "category", "data": EFFORT_LABEL, "position": "top", "axisLine": {"show": False},
               "axisLabel": {"color": "@ink-secondary", "fontSize": 12, "fontWeight": 600}},
        yAxis={"type": "category", "data": list(LADDER.values()), "inverse": True, "axisLine": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500, "margin": 14}},
        series=[{"type": "custom", "renderItem": CELL, "data": cells, "silent": True},
                {"type": "custom", "renderItem": JUMP, "data": jumps, "silent": True}],
    )
    return Figure(option=option, data=rows)
