"""P01: what each monitor setting catches against what it costs, at four audit budgets."""
from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P01",
    "title": "Price is a poor guide to monitoring skill",
    "section": "results",
    "order": 10,
    "caption": ("Each dot is one monitor setting: a model at one reasoning level. Higher catches more of the "
                "500 backdoors; further left costs less per program at list price. Lines join a model's "
                "settings and the dashed line traces the best buys. Bars are 95% intervals.{no_cost}"),
    "notes": [
        "Control Tax (Terekhov et al., 2025) already plots a cost-vs-safety frontier for 13 monitors at a 5% "
        "budget. What's ours is reasoning effort as a second dial, current models, and exact-budget accounting.",
        "Sonnet 5.5 is labelled untrusted monitoring in our runs, but older models wrote the code it reads, so "
        "there's no collusion. Treat it as a reference point, not a trusted monitor a lab would deploy.",
        "Costs are list price times tokens, after Marnick's fixes: cached calls count, and GLM-5.3 is priced at "
        "the discounted rate it is billed at. GLM-5.3's effort=none run is left off: it is max in disguise.",
    ],
    "height": 540,
}

BUDGETS = (0.5, 1, 2, 5)
HIGHLIGHT = ("sonnet55", "haiku55", "haiku45", "glm53")
SHORT = {
    "sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "haiku45": "Haiku 4.5", "glm53": "GLM-5.3",
    "luna": "GPT-6 Luna", "gptoss": "gpt-oss-120b", "qwen38": "Qwen 3.8", "gemini35lite": "Gemini Flash-Lite",
    "gemini35fl": "Gemini Flash", "gemma4": "Gemma 4", "gemma3": "Gemma 3 4B", "gemma3_27b": "Gemma 3 27B",
    "mistrallarge4": "Mistral Large 4", "ministral14b": "Ministral 14B",
}
# Where each model's name sits next to its best point.
LABEL_AT = {
    "sonnet55": "right", "haiku55": "top", "haiku45": "left", "glm53": "right", "mistrallarge4": "right",
    "qwen38": "left", "luna": "left", "gptoss": "top", "gemini35lite": "bottom", "gemini35fl": "right",
    "gemma4": "top", "gemma3": "right", "gemma3_27b": "left", "ministral14b": "right",
}

# Extra points named in the text, labelled as well as each model's best one: (model, effort) -> position.
ALSO_LABEL = {("sonnet55", "low"): "bottom"}


def label_for(model: str, effort: str) -> str:
    """Highlighted models carry the effort of the labelled point; Haiku 4.5 has only one setting."""
    name = SHORT.get(model, model)
    return f"{name} · {effort}" if model in HIGHLIGHT and model != "haiku45" else name


def tip(r) -> str:
    return (f"<b>{r['name']}</b><br>caught {C.pct(r.safety_exact)}% ({C.pct(r.ci_lo)} to {C.pct(r.ci_hi)})"
            f"<br>{C.money(r.cost)} per program")


def series_at(t, budget: float) -> list:
    d = t[(t.budget_pct == budget) & t.cost.notna()]
    out = []
    for model, g in d.groupby("model", sort=False):
        g = g.sort_values("cost")
        hot = model in HIGHLIGHT
        color = entity(model) if hot else "@context-strong"
        best = g.safety_exact.idxmax()
        items = []
        for i, r in g.iterrows():
            item = {"value": [r.cost, round(100 * r.safety_exact, 2)], "tip": tip(r)}
            if i == best or (model, r.effort) in ALSO_LABEL:
                pos = ALSO_LABEL.get((model, r.effort), LABEL_AT.get(model, "right"))
                item["label"] = {"show": True, "position": pos, "formatter": label_for(model, r.effort),
                                 "color": "@ink-primary" if hot else "@ink-muted", "fontSize": 12 if hot else 11,
                                 "fontWeight": 600 if hot else 400, "distance": 7}
            items.append(item)
        hollow = model == "haiku45"
        out.append({
            "name": SHORT.get(model, model), "type": "line", "data": items, "z": 4 if hot else 3,
            "symbol": "circle", "symbolSize": 10 if hot else 7,
            "itemStyle": {"color": "@ink-surface" if hollow else color, "borderColor": color if hollow else "@ink-surface",
                          "borderWidth": 2 if hollow else 1.5},
            "lineStyle": {"color": color if hot else "@context", "width": 1.5, "opacity": 0.65},
            "emphasis": {"focus": "series"},
            # Grey models' names give way when they'd collide; their tooltips still name them.
            **({} if hot else {"labelLayout": {"hideOverlap": True}}),
        })
        if hot:
            out.append({
                "name": SHORT.get(model, model), "type": "custom", "renderItem": C.VBAR, "itemStyle": {"color": color},
                "data": [[r.cost, round(100 * r.ci_lo, 2), round(100 * r.ci_hi, 2)] for _, r in g.iterrows()],
                "encode": {"x": 0, "y": [1, 2]}, "z": 2, "silent": True, "tooltip": {"show": False},
            })
    best, front = -1.0, []
    for _, r in d.sort_values("cost").iterrows():
        if r.safety_exact > best:
            best = r.safety_exact
            front.append([r.cost, round(100 * r.safety_exact, 2)])
    out.append({
        "name": "_best buys", "type": "line", "data": front, "symbol": "none", "z": 1, "silent": True,
        "lineStyle": {"type": "dashed", "color": "@ink-muted", "width": 1.2}, "tooltip": {"show": False},
    })
    return out


def build() -> Figure:
    t = S.run_table(BUDGETS)
    frames = [{"series": series_at(t, b)} for b in BUDGETS]
    no_cost = sorted(t[(t.budget_pct == 2) & t.cost.isna()]["name"].unique())
    option = C.base(
        grid={"left": 58, "right": 30, "top": 20, "bottom": 52, "show": True, "borderWidth": 0,
              "backgroundColor": {"type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 1, "colorStops": [
                  {"offset": 0, "color": "@good/0.11"}, {"offset": 0.5, "color": "@ink-surface/0"},
                  {"offset": 1, "color": "@s7/0.09"}]}},
        xAxis=C.axis("Cost per program, list price (log scale)", type="log", min=0.00005, max=0.05,
                     axisLabel={"formatter": "function (v) { return '$' + v; }"}),
        yAxis=C.axis("Backdoors caught", gap=44, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
        graphic=[{"type": "text", "left": 70, "top": 30, "silent": True,
                  "style": {"text": "↖ better", "fill": "@ink-muted", "fontSize": 12}}],
        series=frames[BUDGETS.index(2)]["series"],
    )
    data = t[["name", "model", "effort", "budget_pct", "cost", "safety_exact", "ci_lo", "ci_hi"]].round(6)
    n = len(no_cost)
    return Figure(
        option=option, data=data,
        dial={"label": "Audit budget", "steps": [f"{b:g}%" for b in BUDGETS], "initial": BUDGETS.index(2), "frames": frames},
        facts={"no_cost": f" {n} setting{'s' if n > 1 else ''} with no recorded cost {'are' if n > 1 else 'is'} left off." if n else ""},
    )
