"""A04: trusted vs untrusted monitoring, as a flow diagram drawn with ECharts graphic elements.

Drawn as ECharts (not an image) so it follows the gallery theme and gets the same copy, PNG and SVG
buttons as every chart. The bots are simple outlined icons (METR-style). Coordinates are in px inside
a 900 px wide group that the chart centres.
"""
from viz.kit import Figure

AUDIT_BUDGET = 2  # percent; the budget the report discusses

META = {
    "id": "A04",
    "title": "Trusted and untrusted monitoring differ only in who watches",
    "section": "intro",
    "order": 30,
    "caption": ("Both protocols score every piece of AI-written code for suspicion and send the top "
                "{budget}% of scores to a human. A trusted monitor is a weaker model we assume can't scheme; "
                "an untrusted monitor is stronger but might collude with the model that wrote the code."),
    "notes": [],
    "height": 600,
}

W = 900
LEFT, RIGHT, MID = 225, 675, 450   # column centres and the shared column
INK = "@ink-primary"
BOT = "@s2"                        # the models that write the code
TRUSTED, UNTRUSTED = "@s0", "@s1"


def text(x, y, s, size=12, weight=400, color="@ink-secondary", align="center"):
    return {"type": "text", "x": x, "y": y, "silent": True,
            "style": {"text": s, "fill": color, "fontSize": size, "fontWeight": weight,
                      "align": align, "verticalAlign": "middle"}}


def rect(x, y, w, h, r=10, fill="@mid", stroke=None, lw=1.5, dash=None):
    return {"type": "rect", "silent": True, "shape": {"x": x, "y": y, "width": w, "height": h, "r": r},
            "style": {"fill": fill, "stroke": stroke or "transparent", "lineWidth": lw if stroke else 0,
                      "lineDash": dash}}


def bot(x, y, fill=BOT, s=1.0):
    """A simple outlined bot head, 50 px wide and 40 px tall at s=1, top-left at (x, y)."""
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


def code_file(x, y, color):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "polygon", "shape": {"points": [[0, 0], [24, 0], [34, 10], [34, 42], [0, 42]]},
         "style": {"fill": "@ink-surface", "stroke": color, "lineWidth": 2, "lineJoin": "round"}},
        {"type": "polyline", "shape": {"points": [[24, 0], [24, 10], [34, 10]]}, "style": {"fill": None, "stroke": color, "lineWidth": 2}},
        {"type": "text", "x": 17, "y": 26, "style": {"text": "</>", "fill": color, "fontSize": 12, "fontWeight": 700,
                                                     "align": "center", "verticalAlign": "middle"}},
    ]}


def magnifier(x, y):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "circle", "shape": {"cx": 11, "cy": 11, "r": 10}, "style": {"fill": None, "stroke": INK, "lineWidth": 3}},
        {"type": "line", "shape": {"x1": 18.5, "y1": 18.5, "x2": 28, "y2": 28}, "style": {"stroke": INK, "lineWidth": 4, "lineCap": "round"}},
    ]}


def person(x, y):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "circle", "shape": {"cx": 11, "cy": 9, "r": 7}, "style": {"fill": INK}},
        {"type": "rect", "shape": {"x": 0, "y": 18, "width": 22, "height": 16, "r": [10, 10, 2, 2]}, "style": {"fill": INK}},
        {"type": "rect", "shape": {"x": 27, "y": 2, "width": 18, "height": 30, "r": 3}, "style": {"fill": None, "stroke": INK, "lineWidth": 2}},
        {"type": "line", "shape": {"x1": 31, "y1": 10, "x2": 41, "y2": 10}, "style": {"stroke": INK, "lineWidth": 2}},
        {"type": "line", "shape": {"x1": 31, "y1": 17, "x2": 41, "y2": 17}, "style": {"stroke": INK, "lineWidth": 2}},
        {"type": "line", "shape": {"x1": 31, "y1": 24, "x2": 38, "y2": 24}, "style": {"stroke": INK, "lineWidth": 2}},
    ]}


def check(x, y, color="@good"):
    return {"type": "group", "x": x, "y": y, "silent": True, "children": [
        {"type": "circle", "shape": {"cx": 15, "cy": 15, "r": 14}, "style": {"fill": None, "stroke": color, "lineWidth": 2.5}},
        {"type": "polyline", "shape": {"points": [[8, 15], [13, 20], [22, 10]]},
         "style": {"fill": None, "stroke": color, "lineWidth": 3, "lineCap": "round", "lineJoin": "round"}},
    ]}


def arrow(points, color, dash=False):
    """A polyline that ends in an arrowhead pointing along its last segment."""
    (x1, y1), (x2, y2) = points[-2], points[-1]
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** .5 or 1
    ux, uy = dx / n, dy / n
    bx, by = x2 - ux * 9, y2 - uy * 9
    head = [[x2, y2], [bx - uy * 5, by + ux * 5], [bx + uy * 5, by - ux * 5]]
    line = points[:-1] + [[bx, by]]
    return [{"type": "polyline", "silent": True, "shape": {"points": line},
             "style": {"stroke": color, "lineWidth": 2, "fill": None, "lineDash": [5, 5] if dash else None}},
            {"type": "polygon", "silent": True, "shape": {"points": head}, "style": {"fill": color}}]


def build() -> Figure:
    g = []
    # Top: the code each protocol has to check, written by a capable model.
    for cx, color in ((LEFT, TRUSTED), (RIGHT, UNTRUSTED)):
        for k in range(3):
            g.append(bot(cx - 118 + k * 56, 8))
        g.append(code_file(cx + 66, 4, color))
        g.append(text(cx, 70, "AI-generated code", 14, 600, INK))
        g += arrow([[cx, 84], [cx, 116]], color)
    # The two monitors.
    for cx, color, name, sub in ((LEFT, TRUSTED, "Trusted monitor", "Weak model, can't scheme or collude"),
                                 (RIGHT, UNTRUSTED, "Untrusted monitor", "Strong model, may scheme or collude")):
        g.append(rect(cx - 170, 118, 340, 72, 14, fill=f"{color}/0.10", stroke=color, lw=1.5))
        g.append(bot(cx - 158, 134, fill=BOT if color == TRUSTED else UNTRUSTED, s=.84))
        g.append(text(cx - 98, 143, name, 15, 700, color if color == UNTRUSTED else INK, "left"))
        g.append(text(cx - 98, 166, sub, 12, 400, "@ink-secondary", "left"))
    # Possible collusion: the untrusted monitor and the model that wrote the code.
    x0 = RIGHT + 170
    g.append({"type": "bezierCurve", "silent": True,
              "shape": {"x1": x0 - 26, "y1": 118, "cpx1": x0 + 48, "cpy1": 104, "cpx2": x0 + 48, "cpy2": 36, "x2": RIGHT + 108, "y2": 30},
              "style": {"stroke": "@s7", "lineWidth": 2, "fill": None, "lineDash": [5, 5]}})
    g.append({"type": "polygon", "silent": True, "shape": {"points": [[RIGHT + 102, 30], [RIGHT + 112, 24], [RIGHT + 112, 36]]},
              "style": {"fill": "@s7"}})
    g.append(text(RIGHT + 116, 62, "Possible", 13, 600, "@s7", "left"))
    g.append(text(RIGHT + 116, 80, "collusion", 13, 600, "@s7", "left"))
    # Both feed one pipeline.
    g += arrow([[LEFT, 190], [LEFT, 222], [MID - 90, 222], [MID - 90, 250]], TRUSTED)
    g += arrow([[RIGHT, 190], [RIGHT, 222], [MID + 90, 222], [MID + 90, 250]], UNTRUSTED)
    g.append(rect(MID - 160, 252, 320, 64, 14, fill="@mid", stroke="@ink-axis", lw=1))
    g.append(magnifier(MID - 138, 268))
    g.append(text(MID - 94, 274, "Suspicion score", 15, 700, INK, "left"))
    g.append(text(MID - 94, 296, "Monitor rates each sample", 12, 400, "@ink-secondary", "left"))
    g += arrow([[MID, 316], [MID, 344]], INK)
    dy, dx, cy = 62, 150, 346 + 62
    g.append({"type": "polygon", "silent": True,
              "shape": {"points": [[MID, cy - dy], [MID + dx, cy], [MID, cy + dy], [MID - dx, cy]]},
              "style": {"fill": "@s6/0.08", "stroke": "@s6", "lineWidth": 1.5, "lineJoin": "round"}})
    g.append({"type": "circle", "silent": True, "shape": {"cx": MID, "cy": cy - 26, "r": 11},
              "style": {"fill": None, "stroke": INK, "lineWidth": 2}})
    g.append(text(MID, cy - 26, "?", 14, 800, INK))
    g.append(text(MID, cy + 2, f"In the top {AUDIT_BUDGET}%", 14, 700, INK))
    g.append(text(MID, cy + 22, "of scores?", 14, 700, INK))
    # Yes: a human audits it. No: it runs.
    out_y, yes_x, no_x = 494, 222, 678
    g += arrow([[MID - 78, cy + 33], [yes_x + 40, out_y - 2]], "@good")
    g.append(text(MID - 150, cy + 52, "Yes", 14, 700, "@good"))
    g += arrow([[MID + 78, cy + 33], [no_x - 40, out_y - 2]], "@s2")
    g.append(text(MID + 150, cy + 52, "No", 14, 700, "@s2"))
    for cx, color, icon, title, sub in ((yes_x, "@good", person, "Human review", "Checked by hand"),
                                         (no_x, "@s2", check, "Allowed to run", "No human review")):
        g.append(rect(cx - 140, out_y, 280, 70, 14, fill=f"{color}/0.10", stroke=color, lw=1.5))
        g.append(icon(cx - 122, out_y + 18) if icon is person else icon(cx - 118, out_y + 20, color))
        g.append(text(cx - 62, out_y + 26, title, 15, 700, INK, "left"))
        g.append(text(cx - 62, out_y + 48, sub, 12, 400, "@ink-secondary", "left"))

    option = {"animation": False, "tooltip": {"show": False},
              "graphic": [{"type": "group", "left": "center", "top": 6, "width": W, "children": g}]}
    return Figure(option=option, facts={"budget": AUDIT_BUDGET})
