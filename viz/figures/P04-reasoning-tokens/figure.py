"""P04: median reasoning tokens per program at each effort setting, for four models that show the range."""
import math

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P04",
    "title": "The same effort setting means very different amounts of thinking",
    "section": "results",
    "order": 40,
    "caption": ("Median reasoning tokens per program at each effort setting, for four models that show the range. "
                "Darker cells think more. The number between two cells is the change; red means it fell."),
    "notes": [
        "Sonnet 5.5 and Mistral Large 4 are left out because they report no reasoning tokens, which doesn't mean "
        "they didn't think. gpt-oss-120b and Gemini Flash-Lite are left out to keep the figure readable; they "
        "step up like Haiku and Luna. All eight are in the CSV.",
    ],
    "height": 300,
}

EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
SHOWN = {"glm53": "GLM-5.3", "haiku55": "Haiku 5.5", "qwen38": "Qwen 3.8", "luna": "GPT-6 Luna"}
ALL = {**SHOWN, "gptoss": "gpt-oss-120b", "gemini35lite": "Gemini Flash-Lite", "sonnet55": "Sonnet 5.5",
       "mistrallarge4": "Mistral Large 4"}
DARK_FROM = 0.55   # cells past this point on the scale get light text

# A rounded cell with its number. value: [column, row, tokens, dark cell?]
CELL = ("function (params, api) { var c = api.coord([api.value(0), api.value(1)]);"
        " var w = api.size([1, 0])[0] * 0.62, h = api.size([0, 1])[1] * 0.64; var v = api.value(2);"
        " var t = String(Math.round(v)).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');"
        " return {type: 'group', children: [{type: 'rect', shape: {x: c[0] - w / 2, y: c[1] - h / 2, width: w, height: h, r: 7},"
        " style: api.style()}, {type: 'text', silent: true, style: {text: t, x: c[0], y: c[1], align: 'center',"
        " verticalAlign: 'middle', fontSize: 15, fontWeight: 600,"
        " fill: api.value(3) ? '@on-strong' : '@on-pale'}}]}; }")

# The change between two cells above a thin connector; size and weight grow with the jump.
# value: [from col, to col, row, delta, size]
JUMP = ("function (params, api) { var a = api.coord([api.value(0), api.value(2)]);"
        " var b = api.coord([api.value(1), api.value(2)]); var w = api.size([1, 0])[0] * 0.31;"
        " var x1 = a[0] + w, x2 = b[0] - w, d = api.value(3), s = api.value(4);"
        " var t = (d >= 0 ? '+' : '−') + String(Math.abs(Math.round(d))).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ',');"
        " return {type: 'group', children: [{type: 'line', shape: {x1: x1 + 3, y1: a[1] + 10, x2: x2 - 3, y2: a[1] + 10},"
        " style: {stroke: api.visual('color'), lineWidth: s > 1 ? 2 : 1}},"
        " {type: 'text', silent: true, style: {text: t, x: (x1 + x2) / 2, y: a[1] - 2, align: 'center',"
        " verticalAlign: 'bottom', fontSize: s > 1 ? 14 : s > 0 ? 12 : 11, fontWeight: s > 0 ? 600 : 400,"
        " fill: api.visual('color')}}]}; }")


def build() -> Figure:
    t = S.run_table()
    runs = t.drop_duplicates("run")
    by_model, rows = {}, []
    for model, label in ALL.items():
        by = {}
        for _, r in runs[runs.model == model].iterrows():
            v = S.median_reasoning(r.run)
            by[EFFORT_ORDER.index(REMAP.get(r.effort, r.effort))] = v
            rows.append({"model": label, "effort": r.effort, "run": r.run, "median_reasoning_tokens": v})
        by_model[model] = by
    top = max(v for m in SHOWN for v in by_model[m].values())
    pos = lambda v: math.sqrt(v / top)   # square root: big amounts look big, small ones stay apart
    cells, jumps = [], []
    for i, model in enumerate(SHOWN):
        by = by_model[model]
        cols = sorted(by)
        for c in cols:
            p = pos(by[c])
            cells.append({"value": [c, i, by[c], int(p >= DARK_FROM)], "itemStyle": {"color": f"@deep:{p:.3f}"}})
        for a, b in zip(cols, cols[1:]):
            d = by[b] - by[a]
            size = 2 if abs(d) >= 500 else 1 if abs(d) >= 150 else 0
            color = "@s7" if d < 0 else "@ink-primary" if size == 2 else "@ink-secondary" if size == 1 else "@ink-muted"
            jumps.append({"value": [a, b, i, d, size], "itemStyle": {"color": color}})
    option = C.base(
        tooltip={"show": False},
        grid={"left": 110, "right": 20, "top": 40, "bottom": 8},
        xAxis={"type": "category", "data": EFFORT_LABEL, "position": "top", "axisLine": {"show": False},
               "axisLabel": {"color": "@ink-secondary", "fontSize": 12, "fontWeight": 600}},
        yAxis={"type": "category", "data": list(SHOWN.values()), "inverse": True, "axisLine": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500, "margin": 14}},
        series=[{"type": "custom", "renderItem": CELL, "data": cells, "silent": True},
                {"type": "custom", "renderItem": JUMP, "data": jumps, "silent": True}],
    )
    return Figure(option=option, data=rows)
