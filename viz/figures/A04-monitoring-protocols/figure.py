"""A04: trusted vs untrusted monitoring, as a flow diagram drawn with ECharts graphic elements.

Drawn as ECharts (not an image) so it follows the gallery theme and gets the same copy, PNG and SVG
buttons as every chart. Coordinates are in px inside a 900 px wide group that the chart centres.
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
    "height": 560,
}

W = 900
LEFT, RIGHT, MID = 225, 675, 450   # panel centres and the shared column
BOX_W = 300
ARROW = "@ink-muted"


def text(x, y, s, size=12, weight=400, color="@ink-secondary", align="center"):
    return {"type": "text", "x": x, "y": y, "silent": True,
            "style": {"text": s, "fill": color, "fontSize": size, "fontWeight": weight,
                      "align": align, "verticalAlign": "middle"}}


def box(cx, y, h, title, sub, w=BOX_W, fill="@mid", stroke=None):
    rect = {"type": "rect", "silent": True, "shape": {"x": cx - w / 2, "y": y, "width": w, "height": h, "r": 8},
            "style": {"fill": fill, "stroke": stroke or "transparent", "lineWidth": 1.5 if stroke else 0}}
    return [rect, text(cx, y + h / 2 - 10, title, 13, 600, "@ink-primary"), text(cx, y + h / 2 + 11, sub)]


def head(x, y, d="down"):
    """A small filled arrowhead with its tip at (x, y)."""
    pts = {"down": [[x - 5, y - 8], [x + 5, y - 8], [x, y]],
           "left": [[x + 8, y - 5], [x + 8, y + 5], [x, y]]}[d]
    return {"type": "polygon", "silent": True, "shape": {"points": pts}, "style": {"fill": ARROW}}


def line(points, dashed=False, color=ARROW):
    return {"type": "polyline", "silent": True, "shape": {"points": points},
            "style": {"stroke": color, "lineWidth": 1.5, "fill": None, "lineDash": [4, 4] if dashed else None}}


def arrow_down(x, y0, y1):
    return [line([[x, y0], [x, y1 - 7]]), head(x, y1)]


def build() -> Figure:
    g = []
    # Two panels: the code and its monitor.
    for cx, name, mon, sub, col in ((LEFT, "Trusted monitoring", "Trusted monitor",
                                     "Weak model, presumably can't scheme or collude", "@s0"),
                                    (RIGHT, "Untrusted monitoring", "Untrusted monitor",
                                     "Strong model that may scheme or collude", "@s1")):
        g.append(text(cx, 14, name, 13, 600, "@ink-primary"))
        g += box(cx, 40, 58, "AI-generated code", "From a capable model")
        g += arrow_down(cx, 98, 140)
        g += box(cx, 140, 64, mon, sub, fill=f"{col}/0.12", stroke=col)
    # The collusion channel on the untrusted side.
    x0 = RIGHT + BOX_W / 2
    g.append({"type": "bezierCurve", "silent": True,
              "shape": {"x1": x0, "y1": 69, "cpx1": x0 + 48, "cpy1": 75, "cpx2": x0 + 48, "cpy2": 166, "x2": x0 + 8, "y2": 172},
              "style": {"stroke": "@s1", "lineWidth": 1.5, "fill": None, "lineDash": [4, 4]}})
    g.append({"type": "polygon", "silent": True,
              "shape": {"points": [[x0 + 9, 167], [x0 + 10, 177], [x0 + 1, 173]]}, "style": {"fill": "@s1"}})
    g.append(text(RIGHT + 10, 119, "Possible collusion", 12, 500, "@s1", "left"))
    # Both monitors feed one shared pipeline.
    g.append(line([[LEFT, 204], [LEFT, 228], [RIGHT, 228], [RIGHT, 204]]))
    g += arrow_down(MID, 228, 258)
    g += box(MID, 258, 58, "Suspicion score", "Monitor rates each sample")
    g += arrow_down(MID, 316, 346)
    dy, dx, cy = 52, 128, 346 + 52
    g.append({"type": "polygon", "silent": True,
              "shape": {"points": [[MID, cy - dy], [MID + dx, cy], [MID, cy + dy], [MID - dx, cy]]},
              "style": {"fill": "@mid", "stroke": "@ink-axis", "lineWidth": 1}})
    g.append(text(MID, cy - 9, f"In the top {AUDIT_BUDGET}%", 13, 600, "@ink-primary"))
    g.append(text(MID, cy + 11, "of scores?", 13, 600, "@ink-primary"))
    # Yes: a human audits it. No: it runs.
    yes_x, no_x, out_y = 230, 670, 476
    g.append(line([[MID - dx, cy], [yes_x, cy], [yes_x, out_y - 7]]))
    g.append(head(yes_x, out_y))
    g.append(text(yes_x + 40, cy - 12, "Yes", 12, 600, "@ink-primary"))
    g.append(line([[MID + dx, cy], [no_x, cy], [no_x, out_y - 7]]))
    g.append(head(no_x, out_y))
    g.append(text(no_x - 40, cy - 12, "No", 12, 600, "@ink-primary"))
    g += box(yes_x, out_y, 58, "Human review", "Checked by hand", w=240)
    g += box(no_x, out_y, 58, "Allowed to run", "No human review", w=240)

    option = {"animation": False, "tooltip": {"show": False},
              "graphic": [{"type": "group", "left": "center", "top": 10, "width": W, "children": g}]}
    return Figure(option=option, facts={"budget": AUDIT_BUDGET})
