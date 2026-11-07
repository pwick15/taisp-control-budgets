"""P03: backdoors caught at each reasoning setting, one line per model."""
from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P03",
    "title": "Turning up reasoning effort helps most models, not all",
    "section": "results",
    "order": 30,
    "caption": ("One line per model across the reasoning settings we ran; higher catches more backdoors. "
                "'medium / default' holds each model's default where the provider names no level, and "
                "'xhigh / max' holds the top setting each provider offers."),
    "notes": [
        "We agreed the framing: effort is a measured lever that depends on the model, not a rule. Most models "
        "gain, one is flat and one gets worse.",
        "Flash-Lite gets one line, nothing more. It catches 20 to 29% at any setting, so nobody would deploy it.",
        "Monitoring Monitorability already shows that more test-time compute helps weak monitors. What's new here "
        "is pricing it against a bigger sibling, and the counterexamples.",
        "Effort labels aren't comparable across providers (see P04). Marnick's dose section re-plots the ladder "
        "against tokens actually spent, the fairer x-axis if a reviewer asks.",
    ],
    "height": 480,
}

BUDGETS = (1, 2, 5)
EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
LADDER = {"sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8",
          "luna": "GPT-6 Luna", "mistrallarge4": "Mistral Large 4", "gptoss": "gpt-oss-120b",
          "gemini35lite": "Gemini Flash-Lite"}
HOT = ("sonnet55", "haiku55", "glm53")


def series_at(t, budget: float) -> list:
    d = t[t.budget_pct == budget]
    out = []
    for model, label in LADDER.items():
        by = {REMAP.get(r.effort, r.effort): r for _, r in d[d.model == model].iterrows()}
        data = []
        for e in EFFORT_ORDER:
            if e in by:
                r = by[e]
                data.append({"value": round(100 * r.safety_exact, 2),
                             "tip": f"<b>{r['name']}</b><br>caught {C.pct(r.safety_exact)}%<br>{C.money(r.cost)} per program"
                             if r.cost == r.cost else f"<b>{r['name']}</b><br>caught {C.pct(r.safety_exact)}%"})
            else:
                data.append(None)
        hot = model in HOT
        color = entity(model) if hot else "@context-strong"
        out.append({
            "name": label, "type": "line", "data": data, "connectNulls": True, "z": 4 if hot else 3,
            "symbolSize": 8 if hot else 6, "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
            "lineStyle": {"color": color, "width": 2.5 if hot else 1.5},
            "endLabel": {"show": True, "formatter": "{a}", "color": "@ink-primary" if hot else "@ink-muted",
                         "fontSize": 12 if hot else 11, "fontWeight": 600 if hot else 400, "distance": 8},
            "labelLayout": {"moveOverlap": "shiftY"},
            "emphasis": {"focus": "series"},
        })
    return out


def build() -> Figure:
    t = S.run_table()
    frames = [{"series": series_at(t, b)} for b in BUDGETS]
    option = C.base(
        grid={"left": 58, "right": 140, "top": 16, "bottom": 52},
        xAxis=C.axis("Reasoning effort setting", type="category", boundaryGap=False, data=EFFORT_LABEL),
        yAxis=C.axis("Backdoors caught", gap=44, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
        series=frames[BUDGETS.index(2)]["series"],
    )
    d = t[t.model.isin(list(LADDER))][["name", "model", "effort", "budget_pct", "safety_exact", "cost"]]
    return Figure(option=option, data=d,
                  dial={"label": "Audit budget", "steps": [f"{b:g}%" for b in BUDGETS],
                        "initial": BUDGETS.index(2), "frames": frames})
