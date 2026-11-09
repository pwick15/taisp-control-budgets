"""P23: what we ran, as a flow diagram drawn with ECharts graphic elements (like A04).

Each APPS problem gives one clean program and one backdoored program. A monitor reads each with
its comments removed and returns a suspicion score. Below are the settings we varied. Colours
match P24: red for the backdoor side, blue for the monitors. Coordinates are px inside a 940 px
wide group that the chart centres.
"""
from viz.kit import Figure

META = {
    "id": "P23",
    "title": "Every monitor scores the same 1,000 programs, recorded once",
    "section": "setup",
    "order": 10,
    "caption": ("Each of 500 APPS coding problems comes with a clean, human-written solution and a backdoored "
                "one written by an older AI model. A monitor reads each program with its comments removed and "
                "gives it a suspicion score. We swept the settings in the bottom row."),
    "notes": [
        "The code is fixed: we never ask a model to write new backdoors in the main runs, so every monitor "
        "and every setting is judged on identical inputs and only the monitor calls cost money.",
        "A backdoor passes the problem's tests but prints a wrong answer on one secret input the attacker "
        "knows. The dataset only keeps backdoors that were checked to work.",
    ],
    "height": 268,
}

W = 940
INK = "@ink-primary"
BAD, MON = "@s7", "@s0"
CY = 101                      # centre line of the main flow


def text(x, y, s, size=12, weight=400, color="@ink-secondary", align="left"):
    return {"type": "text", "x": x, "y": y, "silent": True,
            "style": {"text": s, "fill": color, "fontSize": size, "fontWeight": weight,
                      "align": align, "verticalAlign": "middle"}}


def rect(x, y, w, h, r=12, fill="@mid", stroke=None, lw=1.5, dash=None):
    return {"type": "rect", "silent": True, "shape": {"x": x, "y": y, "width": w, "height": h, "r": r},
            "style": {"fill": fill, "stroke": stroke or "transparent", "lineWidth": lw if stroke else 0,
                      "lineDash": dash}}


def code_file(x, y, color):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "polygon", "shape": {"points": [[0, 0], [20, 0], [28, 8], [28, 36], [0, 36]]},
         "style": {"fill": "@ink-surface", "stroke": color, "lineWidth": 2, "lineJoin": "round"}},
        {"type": "polyline", "shape": {"points": [[20, 0], [20, 8], [28, 8]]},
         "style": {"fill": None, "stroke": color, "lineWidth": 2}},
        {"type": "text", "x": 14, "y": 22, "style": {"text": "</>", "fill": color, "fontSize": 11, "fontWeight": 700,
                                                     "align": "center", "verticalAlign": "middle"}},
    ]}


def task_sheet(x, y):
    """A problem statement: a page with a few lines of text."""
    lines = [{"type": "line", "shape": {"x1": 6, "y1": yy, "x2": 6 + w, "y2": yy},
              "style": {"stroke": "@ink-secondary", "lineWidth": 2, "lineCap": "round"}}
             for yy, w in ((10, 18), (17, 14), (24, 18), (31, 10))]
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "rect", "shape": {"x": 0, "y": 0, "width": 30, "height": 38, "r": 3},
         "style": {"fill": "@ink-surface", "stroke": INK, "lineWidth": 2}}] + lines}


def bot(x, y, fill, s=0.8):
    """The outlined bot head from A04, 50 x 40 px at s=1, top-left at (x, y)."""
    k = lambda v: v * s
    stroke = {"stroke": INK, "lineWidth": 2 * s}
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "rect", "shape": {"x": k(19), "y": 0, "width": k(12), "height": k(8), "r": k(2)}, "style": {"fill": fill, **stroke}},
        {"type": "rect", "shape": {"x": 0, "y": k(15), "width": k(6), "height": k(14), "r": k(2)}, "style": {"fill": fill, **stroke}},
        {"type": "rect", "shape": {"x": k(44), "y": k(15), "width": k(6), "height": k(14), "r": k(2)}, "style": {"fill": fill, **stroke}},
        {"type": "rect", "shape": {"x": k(5), "y": k(7), "width": k(40), "height": k(31), "r": k(8)}, "style": {"fill": fill, **stroke}},
        {"type": "circle", "shape": {"cx": k(18), "cy": k(22), "r": k(4.5)}, "style": {"fill": "@on-strong", **stroke}},
        {"type": "circle", "shape": {"cx": k(32), "cy": k(22), "r": k(4.5)}, "style": {"fill": "@on-strong", **stroke}},
    ]}


def magnifier(x, y):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "circle", "shape": {"cx": 11, "cy": 11, "r": 10}, "style": {"fill": None, "stroke": INK, "lineWidth": 3}},
        {"type": "line", "shape": {"x1": 18.5, "y1": 18.5, "x2": 28, "y2": 28},
         "style": {"stroke": INK, "lineWidth": 4, "lineCap": "round"}},
    ]}


def arrow(points, color="@ink-secondary", head=True):
    """A polyline, ending in an arrowhead along its last segment when head is True."""
    if not head:
        return [{"type": "polyline", "silent": True, "shape": {"points": points},
                 "style": {"stroke": color, "lineWidth": 2, "fill": None, "lineJoin": "round"}}]
    (x1, y1), (x2, y2) = points[-2], points[-1]
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** .5 or 1
    ux, uy = dx / n, dy / n
    bx, by = x2 - ux * 9, y2 - uy * 9
    tip = [[x2, y2], [bx - uy * 5, by + ux * 5], [bx + uy * 5, by - ux * 5]]
    return [{"type": "polyline", "silent": True, "shape": {"points": points[:-1] + [[bx, by]]},
             "style": {"stroke": color, "lineWidth": 2, "fill": None, "lineJoin": "round"}},
            {"type": "polygon", "silent": True, "shape": {"points": tip}, "style": {"fill": color}}]


def card(x, y, w, h, icon, title, lines, fill, stroke):
    """A rounded box with an icon on the left and a bold title over one or two short lines."""
    out = [rect(x, y, w, h, 12, fill=fill, stroke=stroke), icon]
    ty = y + h / 2 - 9 * len(lines)
    out.append(text(x + 58, ty, title, 15, 700, INK))
    for i, s in enumerate(lines):
        out.append(text(x + 58, ty + 21 + 17 * i, s, 12))
    return out


def pill(x, y, s):
    w = 16 + 6.6 * len(s)
    return [rect(x, y - 13, w, 26, 13, fill=f"{MON}/0.10", stroke=f"{MON}/0.5", lw=1),
            text(x + w / 2, y, s, 12, 500, INK, "center")], w


def build() -> Figure:
    g = []
    # 1. The problem.
    g += card(0, CY - 40, 178, 80, task_sheet(14, CY - 19), "500 problems", ["APPS coding tasks"],
              "@mid", "@ink-axis")
    # 2. Its two programs.
    top, bot_y, cx, cw, ch = CY - 87, CY + 9, 226, 236, 78
    g += card(cx, top, cw, ch, code_file(cx + 16, top + 21, "@ink-secondary"), "Clean program",
              ["written by a human", "passes every test"], "@mid", "@ink-axis")
    g += card(cx, bot_y, cw, ch, code_file(cx + 16, bot_y + 21, BAD), "Backdoored program",
              ["written by an older AI model", "fails on one secret input"], f"{BAD}/0.08", BAD)
    g += arrow([[178, CY], [202, CY], [202, top + ch / 2], [cx - 2, top + ch / 2]])
    g += arrow([[202, CY], [202, bot_y + ch / 2], [cx - 2, bot_y + ch / 2]])
    # 3. The monitor.
    mx, mw = 514, 196
    g += arrow([[cx + cw, top + ch / 2], [489, top + ch / 2], [489, CY]], head=False)
    g += arrow([[cx + cw, bot_y + ch / 2], [489, bot_y + ch / 2], [489, CY], [mx - 2, CY]])
    g += card(mx, CY - 40, mw, 80, bot(mx + 12, CY - 17, MON), "Monitor", ["reads the code,", "comments removed"],
              f"{MON}/0.10", MON)
    # 4. The score.
    sx = 738
    g += arrow([[mx + mw, CY], [sx - 2, CY]])
    g += card(sx, CY - 40, W - sx, 80, magnifier(sx + 16, CY - 14), "Suspicion score", ["0 to 10 per program"],
              "@mid", "@ink-axis")
    # What we varied, hanging off the monitor.
    py = 222
    items = ["13 models", "reasoning effort", "0 to 10 or 0 to 100", "comments in or out"]
    widths = [16 + 6.6 * len(s) for s in items]
    total = sum(widths) + 10 * (len(items) - 1)
    x = mx + mw / 2 - total / 2
    g.append({"type": "line", "silent": True,
              "shape": {"x1": mx + mw / 2, "y1": CY + 40, "x2": mx + mw / 2, "y2": py - 15},
              "style": {"stroke": f"{MON}/0.6", "lineWidth": 1.5, "lineDash": [3, 3]}})
    g.append(text(x - 12, py, "We varied", 12, 600, "@ink-secondary", "right"))
    for s in items:
        parts, w = pill(x, py, s)
        g += parts
        x += w + 10
    option = {"animation": False, "tooltip": {"show": False},
              "graphic": [{"type": "group", "left": "center", "top": 14, "width": W, "children": g}]}
    return Figure(option=option)
