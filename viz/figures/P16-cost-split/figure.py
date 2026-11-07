"""P16: cost per program split into price per token and tokens used, for every priced monitor setting."""
import json
import math

import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P16",
    "title": "GLM-5.3 has cheaper tokens than Sonnet but uses {ratio:.0f}x as many",
    "section": "recommendations",
    "order": 10,
    "caption": ("Each dot is one monitor setting: what it paid per million tokens, input and output together "
                "(across), and how many tokens it used per program (up). Cost per program is the product, so dots "
                "on one diagonal cost the same. Prices are the list prices behind P01."),
    "notes": [
        "GLM-5.3 at max costs {glm_x:.1f}x Sonnet per program although its tokens cost about half as much: the "
        "difference is volume, mostly hidden reasoning (M20). Sonnet being cheaper per program needs no subsidy "
        "to explain it.",
        "Haiku 4.5 uses about as many tokens as Haiku 5.5 but its list price per token is ten times higher, so it "
        "costs {h45_x:.1f}x Haiku 5.5's default per program and catches fewer backdoors.",
        "List prices change; tokens per program don't. Reporting both lets anyone reprice these results later.",
    ],
    "height": 520,
}

SHOW = {S.SONNET: "Sonnet 5.5 · high", "dataset-glm53-tm-n500-strip": "GLM-5.3 · max",
        "dataset-haiku45-tm-n500-strip": "Haiku 4.5", S.HAIKU_X: "Haiku 5.5 · xhigh",
        S.HAIKU_DEFAULT: "Haiku 5.5 · default"}
LABEL_AT = {S.SONNET: "right", "dataset-glm53-tm-n500-strip": "right", "dataset-haiku45-tm-n500-strip": "left",
            S.HAIKU_X: "top", S.HAIKU_DEFAULT: "bottom"}
ISO = [(0.0001, "$0.0001"), (0.001, "$0.001"), (0.01, "$0.01")]


def tokens(run: str) -> float:
    row = pd.read_csv(S.RESULTS / f"{run}.csv").iloc[0]
    return float(sum(json.loads(row["tokens_per_sample"]).values()))


def build() -> Figure:
    t = S.run_table()
    d = t[(t.budget_pct == 2) & t.cost.notna()].copy()
    d["tokens"] = [tokens(r) for r in d.run]
    d["price"] = 1e6 * d.cost / d.tokens
    lo_x, hi_x = 10 ** math.floor(math.log10(d.price.min())), 10 ** math.ceil(math.log10(d.price.max()))
    lo_y, hi_y = 10 ** math.floor(math.log10(d.tokens.min())), 10 ** math.ceil(math.log10(d.tokens.max()))
    series = []
    for cost, label in ISO:
        xs = [x for x in (lo_x, hi_x)]
        pts = [[x, cost * 1e6 / x] for x in xs]
        series.append({"name": f"_iso {label}", "type": "line", "data": pts, "symbol": "none", "silent": True, "z": 1,
                       "lineStyle": {"type": "dashed", "color": "@ink-axis", "width": 1}, "tooltip": {"show": False},
                       "endLabel": {"show": False},
                       # Name each diagonal near the top edge, where the three sit well apart.
                       "markPoint": {"silent": True, "symbol": "circle", "symbolSize": 0,
                                     "data": [{"coord": [x, y], "value": f"{label} per program"}
                                              for y in [hi_y * 0.78] for x in [cost * 1e6 / y]
                                              if lo_x <= x <= hi_x / 3],
                                     "label": {"show": True, "formatter": "{c}", "color": "@ink-muted", "fontSize": 11,
                                               "position": "right", "distance": 6}}})
    grey, hot = [], []
    for _, r in d.iterrows():
        item = {"value": [round(r.price, 4), round(r.tokens)],
                "tip": f"<b>{r['name']}</b><br>${r.price:.2f} per million tokens<br>{r.tokens:,.0f} tokens per program"
                       f"<br>{C.money(r.cost)} per program, catches {C.pct(r.safety_exact)}% at 2%"}
        if r.run in SHOW:
            item["itemStyle"] = {"color": "@ink-surface" if r.model == "haiku45" else entity(r.model),
                                 "borderColor": entity(r.model), "borderWidth": 2 if r.model == "haiku45" else 1.5}
            item["label"] = {"show": True, "formatter": SHOW[r.run], "position": LABEL_AT[r.run], "distance": 8,
                             "color": "@ink-primary", "fontSize": 12, "fontWeight": 600}
            hot.append(item)
        else:
            grey.append(item)
    series.append({"name": "Other settings", "type": "scatter", "data": grey, "symbolSize": 7, "z": 3,
                   "itemStyle": {"color": "@context-strong", "borderColor": "@ink-surface", "borderWidth": 1}})
    series.append({"name": "Discussed", "type": "scatter", "data": hot, "symbolSize": 11, "z": 4,
                   "itemStyle": {"borderColor": "@ink-surface", "borderWidth": 1.5}})
    option = C.base(
        grid={"left": 64, "right": 40, "top": 24, "bottom": 54},
        xAxis=C.axis("Price per million tokens (USD, log scale)", type="log", min=lo_x, max=hi_x,
                     axisLabel={"formatter": "function (v) { return '$' + v; }"}),
        yAxis=C.axis("Tokens per program (log scale)", gap=48, type="log", min=lo_y, max=hi_y),
        series=series,
    )
    at = lambda run: d[d.run == run].iloc[0]
    s, g, h45, h55 = at(S.SONNET), at("dataset-glm53-tm-n500-strip"), at("dataset-haiku45-tm-n500-strip"), at(S.HAIKU_DEFAULT)
    data = d[["name", "model", "effort", "price", "tokens", "cost", "safety_exact"]].rename(
        columns={"price": "usd_per_million_tokens", "tokens": "tokens_per_program", "cost": "usd_per_program",
                 "safety_exact": "caught_at_2pct"})
    return Figure(option=option, data=data,
                  facts={"ratio": g.tokens / s.tokens, "glm_x": g.cost / s.cost, "h45_x": h45.cost / h55.cost})
