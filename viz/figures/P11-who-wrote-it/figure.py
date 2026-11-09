"""P11: for each model that wrote backdoors, the share that got past all seven of our monitors."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P11",
    "title": "Some writers' backdoors get past every monitor far more often",
    "section": "results",
    "order": 110,
    "caption": ("Share of each model's backdoors that all seven of our monitors missed at a 2% budget, with how "
                "many it wrote. Faint bars are 95% ranges; the dashed line is all 500 backdoors together."),
    "notes": [
        "Most groups are small and their ranges overlap. Only the gap between o1-mini and o3-mini is clearly "
        "real, so say this with the caveat that more backdoors per model are needed.",
        "Models didn't write backdoors for the same problems, so problem difficulty is mixed in with the "
        "writer's skill. A fair test would have every model attack the same problems.",
        "Neither release date (P22) nor general capability (P26) explains the spread.",
        "The CSV also splits each writer's backdoors into missed by some and caught by all seven, which the "
        "earlier version of this figure drew.",
        "For the recommendations: report catch rates per attack source, not just the average.",
    ],
}

NAMES = {
    "unknown": "Original APPS set", "openai/o1-mini": "o1-mini", "openai/o3-mini": "o3-mini",
    "openai/gpt-4o-mini": "GPT-4o mini", "openai/gpt-4o": "GPT-4o", "openai/gpt-3.5-turbo": "GPT-3.5 Turbo",
    "anthropic/claude-3-5-haiku-latest": "Claude 3.5 Haiku", "anthropic/claude-3-7-sonnet-latest": "Claude 3.7 Sonnet",
    "anthropic/claude-3-7-sonnet-thinking-latest": "Claude 3.7 Sonnet thinking",
    "google/gemini-2.0-flash": "Gemini 2.0 Flash",
}

# A soft horizontal bar behind a dot, for its 95% range. Data: [lo, hi, row].
HBAR = ("function (params, api) { var a = api.coord([api.value(0), api.value(2)]);"
        " var b = api.coord([api.value(1), api.value(2)]);"
        " return {type: 'line', shape: {x1: a[0], y1: a[1], x2: b[0], y2: b[1]},"
        " style: {stroke: api.visual('color'), lineWidth: 8, lineCap: 'round', opacity: 0.2}, silent: true}; }")


def build() -> Figure:
    cf = S.cases()
    g = cf.groupby("model").agg(n=("caught_by", "size"), missed_all=("caught_by", lambda s: int((s == 0).sum())),
                                missed_some=("caught_by", lambda s: int(((s > 0) & (s < 7)).sum())),
                                caught_all=("caught_by", lambda s: int((s == 7).sum())),
                                median_lines=("changed_lines", "median")).reset_index()
    g["missed_all_share"] = g.missed_all / g.n
    g = g.sort_values(["missed_all_share", "n"], ascending=[False, False]).reset_index(drop=True)
    g["writer"] = [NAMES.get(m, m.split("/")[-1].replace("-latest", "")) for m in g.model]
    g["lo"], g["hi"] = zip(*[S.wilson(int(k), int(n)) for k, n in zip(g.missed_all, g.n)])
    overall = float(g.missed_all.sum() / g.n.sum())

    cats = [f"{r.writer}|{r.n} written" for r in g.itertuples()]
    dots = [{"value": [round(100 * r.missed_all_share, 2), i],
             "tip": (f"<b>{r.writer}</b><br>{r.missed_all} of {r.n} missed by all seven"
                     f"<br>95% range {100 * r.lo:.0f}–{100 * r.hi:.0f}%")}
            for i, r in enumerate(g.itertuples())]
    option = C.base(
        grid={"left": 16, "right": 30, "top": 30, "bottom": 50, "containLabel": True},
        xAxis=C.axis("Missed by all seven monitors", gap=30, type="value", min=0, max=50, interval=10,
                     axisLabel={"formatter": "{value}%"}),
        yAxis={"type": "category", "data": cats, "inverse": True, "axisLine": {"show": False},
               "axisTick": {"show": False},
               "axisLabel": {"formatter": "function (v) { var p = v.split('|'); return '{n|' + p[0] + '}  {c|' + p[1] + '}'; }",
                             "rich": {"n": {"color": "@ink-primary", "fontSize": 13, "fontWeight": 500},
                                      "c": {"color": "@ink-muted", "fontSize": 11}}}},
        series=[
            {"name": "_range", "type": "custom", "renderItem": HBAR, "itemStyle": {"color": "@s7"},
             "data": [[round(100 * r.lo, 2), round(100 * r.hi, 2), i] for i, r in enumerate(g.itertuples())],
             "encode": {"x": [0, 1], "y": 2}, "z": 1, "silent": True, "tooltip": {"show": False}},
            {"name": "missed by all seven", "type": "scatter", "symbolSize": 11, "z": 3, "data": dots,
             "itemStyle": {"color": "@s7", "borderColor": "@ink-surface", "borderWidth": 1.5},
             "label": {"show": True, "position": "top", "distance": 5, "formatter":
                       "function (p) { return Math.round(p.value[0]) + '%'; }",
                       "color": "@ink-primary", "fontSize": 11, "fontWeight": 600}},
            {"name": "_all", "type": "line", "data": [], "silent": True,
             "markLine": {"silent": True, "symbol": "none",
                          "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1.2},
                          "label": {"formatter": f"all {100 * overall:.0f}%", "position": "start",
                                    "color": "@ink-muted", "fontSize": 11},
                          "data": [{"xAxis": round(100 * overall, 2)}]}},
        ],
    )
    return Figure(option=option, height=108 + 38 * len(g),
                  data=g[["writer", "model", "n", "missed_all", "missed_some", "caught_all", "lo", "hi",
                          "median_lines"]])
