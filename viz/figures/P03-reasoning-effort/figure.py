"""P03: backdoors caught at each reasoning setting, one line per model, coloured by what more effort did.

Blue: the model catches more backdoors at its highest setting than at its lowest, at a 2% budget. Red: it
catches fewer. P17 uses the same rule and colours, so the two figures read as a pair. The grouping is fixed
at 2% and kept when the dial moves, so a line never changes colour mid-GIF.
"""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P03",
    "title": "Turning up reasoning effort helps most models, not all",
    "section": "results",
    "order": 30,
    "caption": ("One line per model across the reasoning settings we ran; higher catches more backdoors. Blue "
                "models catch more at their highest setting than their lowest, at a 2% budget; red ones catch "
                "fewer. 'medium / default' holds each model's default where the provider names no level."),
    "notes": [
        "Grouped by the sign of the lowest-to-highest change at 2%. Two changes are small: Sonnet's "
        "{son:+.1f} (paired 95% interval {son_lo:+.1f} to {son_hi:+.1f}), since it starts near the top, and "
        "Mistral's {mis:+.1f} ({mis_lo:+.1f} to {mis_hi:+.1f}), whose interval spans zero.",
        "Flash-Lite catches 20 to 29% at any setting, so nobody would deploy it. It's red as a counterexample, "
        "not as a contender.",
        "Monitoring Monitorability already shows that more test-time compute helps weak monitors. What's new here "
        "is pricing it against a bigger sibling, and the counterexamples.",
        "Effort labels aren't comparable across providers (see P04). Marnick's dose section re-plots the ladder "
        "against tokens actually spent, the fairer x-axis if a reviewer asks.",
    ],
    "height": 500,
}

BUDGETS = (1, 2, 5)
EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
RANK = {e: i for i, e in enumerate(["off", "low", "medium", "default", "high", "xhigh", "max"])}
LADDER = {"sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8",
          "luna": "GPT-6 Luna", "mistrallarge4": "Mistral Large 4", "gptoss": "gpt-oss-120b",
          "gemini35lite": "Gemini Flash-Lite"}
# group: (colour, line width, marker size, label colour, label size, label weight, z)
STYLE = {"up": ("@s0", 2.5, 8, "@ink-primary", 12, 600, 4),
         "down": ("@s7", 2.5, 8, "@ink-primary", 12, 600, 5)}
NAMES = {"up": "Caught more with effort", "down": "Caught fewer with effort"}


def ends(model: str) -> tuple[str, str]:
    """A model's lowest and highest reasoning setting we ran, as run names."""
    runs = sorted((RANK[e], r) for r, (_, m, _, e) in S.RUNS.items() if m == model and r not in S.EXCLUDE)
    return runs[0][1], runs[-1][1]


def classify() -> tuple[dict, dict]:
    """Group per model, plus each model's change at 2% with its paired interval (points)."""
    group, change = {}, {}
    for model in LADDER:
        lo, hi = ends(model)
        d = S.paired_diff(hi, lo, (2,)).iloc[0]
        c = (100 * d["diff"], 100 * d["lo"], 100 * d["hi"])
        change[model] = c
        group[model] = "up" if c[0] > 0 else "down"
    return group, change


def series_at(t, budget: float, group: dict, names: dict) -> list:
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
        color, width, size, ink, fs, fw, z = STYLE[group[model]]
        out.append({
            "name": names[group[model]], "type": "line", "data": data, "connectNulls": True, "z": z,
            "symbolSize": size, "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
            "lineStyle": {"color": color, "width": width},
            "endLabel": {"show": True, "formatter": label, "color": ink, "fontSize": fs, "fontWeight": fw,
                         "distance": 8},
            "labelLayout": {"moveOverlap": "shiftY"},
            "emphasis": {"focus": "series"},
        })
    return out


def build() -> Figure:
    t = S.run_table()
    group, change = classify()
    frames = [{"series": series_at(t, b, group, NAMES)} for b in BUDGETS]
    option = C.base(
        grid={"left": 58, "right": 140, "top": 44, "bottom": 52},
        legend={"top": 0, "left": 0, "data": list(NAMES.values()), "selectedMode": False},
        xAxis=C.axis("Reasoning effort setting", type="category", boundaryGap=False, data=EFFORT_LABEL),
        yAxis=C.axis("Backdoors caught", gap=44, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
        series=frames[BUDGETS.index(2)]["series"],
    )
    d = t[t.model.isin(list(LADDER))][["name", "model", "effort", "budget_pct", "safety_exact", "cost"]].copy()
    d["group_at_2pct"] = d.model.map(group)
    son, mis = change["sonnet55"], change["mistrallarge4"]
    return Figure(option=option, data=d,
                  facts={"son": son[0], "son_lo": son[1], "son_hi": son[2],
                         "mis": mis[0], "mis_lo": mis[1], "mis_hi": mis[2]},
                  dial={"label": "Audit budget", "steps": [f"{b:g}%" for b in BUDGETS],
                        "initial": BUDGETS.index(2), "frames": frames})
