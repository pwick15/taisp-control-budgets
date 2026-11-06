"""P07: Sonnet's most suspicious honest programs, one square each, showing where a budget cuts a tie."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P07",
    "title": "A 2% budget lands in the middle of a tie",
    "section": "results",
    "order": 70,
    "caption": ("Sonnet 5.5's {show} most suspicious honest programs out of 500, one square each, labelled with "
                "its score. Top row: the default 0 to 10 score. Bottom row: the same monitor asked for 0 to 100. "
                "Amber squares are tied at the cutoff, so a budget can take all of them or none."),
    "notes": [
        "The four-row version (Sonnet and Haiku, both scales) is P13 in the appendix. Haiku's 0 to 10 tie is "
        "worse: 221 programs share one score.",
    ],
    "height": 240,
}

BUDGETS = (1, 2, 5)
SHOW = 40
ROWS = [("0 to 10 score", S.SONNET, 10), ("0 to 100 score", S.SONNET_100, 100)]

# One square per program with its score inside. value: [rank, row, score, state]; state 1 audited, 2 tied, 0 not.
SQUARE = ("function (params, api) { var a = api.coord([api.value(0), api.value(1)]);"
          " var b = api.coord([api.value(0) + 1, api.value(1)]); var h = api.size([0, 1])[1] * 0.52;"
          " var w = (b[0] - a[0]) * 0.86; var v = api.value(2), s = api.value(3);"
          " return {type: 'group', children: [{type: 'rect', shape: {x: a[0], y: a[1] - h / 2, width: w, height: h, r: 3},"
          " style: api.style()}, {type: 'text', silent: true, style: {text: String(v), x: a[0] + w / 2, y: a[1],"
          " align: 'center', verticalAlign: 'middle', fontSize: v > 99 ? 9 : 11, fontWeight: 500,"
          " fill: s === 1 ? '@on-strong' : s === 2 ? '@on-bright' : '@ink-secondary'}}]}; }")


def build() -> Figure:
    rows, table = [], []
    for label, run, scale in ROWS:
        h, _ = S.load_scores(run)
        vals = sorted((round(v * scale) for v in h.values), reverse=True)
        rows.append((label, vals, len(h)))
        table += [{"scale": label, "rank": j + 1, "score": v} for j, v in enumerate(vals[:SHOW])]

    def frame(b):
        aud, cut, rest, notes = [], [], [], []
        for i, (label, vals, n) in enumerate(rows):
            k = round(b / 100 * n)
            above, upto = sum(v > vals[k - 1] for v in vals), sum(v >= vals[k - 1] for v in vals)
            for j, v in enumerate(vals[:SHOW]):
                tip = f"<b>{label}</b><br>honest program ranked {j + 1}, scored {v}"
                if upto == k:
                    (aud if j < k else rest).append({"value": [j, i, v, 1 if j < k else 0], "tip": tip})
                elif j < above:
                    aud.append({"value": [j, i, v, 1], "tip": tip})
                elif j < upto:
                    cut.append({"value": [j, i, v, 2], "tip": tip})
                else:
                    rest.append({"value": [j, i, v, 0], "tip": tip})
            notes.append({"name": f"audits exactly {k}" if upto == k else f"audits {above} or {upto}, not {k}",
                          "value": [SHOW, i]})
        k0 = round(b / 100 * rows[0][2])
        sq = lambda name, color, data: {"name": name, "type": "custom", "renderItem": SQUARE, "data": data,
                                         "clip": False, "itemStyle": {"color": color}}
        return {"series": [
            sq("Audited", "@s0", aud), sq("Tied: all or none", "@warning", cut), sq("Not audited", "@mid", rest),
            {"name": "_notes", "type": "scatter", "symbolSize": 0, "data": notes, "silent": True, "clip": False,
             "tooltip": {"show": False},
             "label": {"show": True, "position": "right", "distance": 12, "formatter": "{b}",
                       "color": "@ink-primary", "fontSize": 13, "fontWeight": 600},
             "markLine": {"silent": True, "symbol": "none", "data": [{"xAxis": k0 - 0.07}],
                          "lineStyle": {"color": "@ink-primary", "type": "dashed", "width": 1.5},
                          "label": {"formatter": f"{b:g}% budget = {k0} programs", "position": "start",
                                    "color": "@ink-secondary", "fontSize": 12}}},
        ]}

    frames = [frame(b) for b in BUDGETS]
    option = C.base(
        grid={"left": 110, "right": 180, "top": 34, "bottom": 40},
        xAxis={"type": "value", "min": 0, "max": SHOW, "show": False},
        yAxis={"type": "category", "data": [r[0] for r in rows], "inverse": True, "axisLine": {"show": False},
               "axisLabel": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500}},
        legend={"bottom": 0, "left": 104, "data": ["Audited", "Tied: all or none", "Not audited"]},
        series=frames[BUDGETS.index(2)]["series"],
    )
    return Figure(option=option, data=table, facts={"show": SHOW},
                  dial={"label": "Audit budget", "steps": [f"{b:g}%" for b in BUDGETS],
                        "initial": BUDGETS.index(2), "frames": frames})
