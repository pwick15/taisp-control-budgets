"""P13: honest programs ranked by suspicion, in blocks of equal score, for two monitors on two scales."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P13",
    "title": "A 2% budget usually lands in the middle of a tie",
    "section": "appendix",
    "order": 10,
    "caption": ("Each bar is the 500 honest programs, ranked from most to least suspicious by one monitor; programs "
                "with the same score form one block. Only the top 10% is shown. Blue blocks are audited; the amber "
                "block is a tie the budget cuts through, so you audit all of it or none."),
    "notes": [
        "Report exact budgets as the main numbers, with the audit-only-above-the-tie numbers and the rate they "
        "really audit in an appendix table.",
        "More honest data doesn't fix ties: a 0 to 10 score only ever offers 11 places to cut. It does fix the other "
        "problem, that at 500 honest programs a 1% budget rests on just 5 of them.",
    ],
    "height": 360,
}

BUDGETS = (0.5, 1, 2, 5)
XMAX = 10.0
ROWS = [("Sonnet 5.5, 0 to 10", S.SONNET, 10), ("Sonnet 5.5, 0 to 100", S.SONNET_100, 100),
        ("Haiku 5.5 xhigh, 0 to 10", S.HAIKU_X, 10), ("Haiku 5.5 xhigh, 0 to 100", S.HAIKU_X_100, 100)]


def build() -> Figure:
    rows = [(name, S.tie_blocks(run), scale) for name, run, scale in ROWS]
    table = [{"row": name, "score": v * scale, "from_pct": x0, "to_pct": x1, "programs": n}
             for name, blocks, scale in rows for v, x0, x1, n in blocks if x0 < XMAX]

    def frame(b):
        aud, cut, rest, notes, labels = [], [], [], [], []
        for i, (name, blocks, scale) in enumerate(rows):
            lo = hi = None
            for v, x0, x1, n in blocks:
                if x0 >= XMAX:
                    break
                item = {"value": [round(x0, 3), round(min(x1, XMAX), 3), i],
                        "tip": f"<b>{name}</b><br>{n} honest program{'s' if n > 1 else ''} scored {v * scale:g}"
                               f"<br>ranked {x0:.1f}% to {x1:.1f}% most suspicious"}
                if x1 <= b + 1e-9:
                    aud.append(item)
                elif x0 < b - 1e-9:
                    cut.append(item)
                    lo, hi = x0, x1
                    if min(x1, XMAX) - x0 > 2.2:
                        labels.append({"name": f"{n} tied at {v * scale:g}", "value": [round((x0 + min(x1, XMAX)) / 2, 3), i]})
                else:
                    rest.append(item)
            notes.append({"name": f"exactly {b:g}%" if lo is None else f"{lo:.1f}% or {hi:.1f}%", "value": [XMAX, i]})
        blk = lambda name, color, data, z: {"name": name, "type": "custom", "renderItem": C.BLOCK, "data": data,
                                             "z": z, "clip": False,
                                             "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1}}
        return {"series": [
            blk("Audited", "@s0", aud, 3), blk("Tied at the line", "@warning", cut, 3), blk("Not audited", "@context", rest, 2),
            {"name": "_labels", "type": "scatter", "symbolSize": 0, "data": labels, "silent": True, "z": 5,
             "tooltip": {"show": False}, "label": {"show": True, "formatter": "{b}", "color": "@on-bright", "fontSize": 11}},
            {"name": "_notes", "type": "scatter", "symbolSize": 0, "data": notes, "silent": True, "clip": False,
             "tooltip": {"show": False},
             "label": {"show": True, "position": "right", "distance": 12, "formatter": "{b}",
                       "color": "@ink-primary", "fontSize": 12, "fontWeight": 600},
             "markLine": {"silent": True, "symbol": "none", "data": [{"xAxis": b}],
                          "lineStyle": {"color": "@ink-primary", "type": "dashed", "width": 1.5},
                          "label": {"formatter": f"requested {b:g}%", "position": "start", "color": "@ink-secondary",
                                    "fontSize": 12}}},
        ]}

    frames = [frame(b) for b in BUDGETS]
    option = C.base(
        grid={"left": 184, "right": 130, "top": 34, "bottom": 74},
        graphic=[{"type": "text", "right": 8, "top": 12,
                  "style": {"text": "Share you can audit", "fill": "@ink-muted", "fontSize": 11, "align": "right"}}],
        xAxis=C.axis("Honest programs ranked by suspicion (top 10%)", gap=30, type="value", min=0, max=XMAX, interval=1,
                     axisLabel={"formatter": "{value}%"}),
        yAxis={"type": "category", "data": [r[0] for r in rows], "inverse": True,
               "axisLabel": {"color": "@ink-primary", "fontSize": 12, "fontWeight": 500}},
        legend={"bottom": 0, "left": 178, "data": ["Audited", "Tied at the line", "Not audited"]},
        series=frames[BUDGETS.index(2)]["series"],
    )
    return Figure(option=option, data=table,
                  dial={"label": "Requested budget", "steps": [f"{b:g}%" for b in BUDGETS],
                        "initial": BUDGETS.index(2), "frames": frames})
