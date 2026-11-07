"""A06: as reasoning effort rises, catches go up (top) while false alarms on clean code stay flat (bottom)."""
from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "A06",
    "title": "More reasoning catches more backdoors without raising false alarms",
    "section": "results",
    "order": 35,
    "caption": ("Top: backdoors caught at a 2% audit budget at each reasoning setting, with 95% intervals. "
                "Bottom: share of the {n_clean} clean programs the same monitors score at or above the dial's "
                "level, same colours. Detection rises by up to {max_gain:.0f} points while false alarms stay near zero."),
    "notes": [
        "Paired by program, lowest against highest effort, no model's false alarms rose significantly at any of "
        "the three levels. The biggest change at 5 or more is one program in 500.",
        "At a fixed budget the flagged share of clean code is fixed by design, so the bottom panel uses absolute "
        "score levels. That is what shows clean code isn't scored as more suspicious.",
        "Not every model gains: Gemini Flash-Lite catches fewer backdoors as effort rises and Mistral Large 4 is "
        "flat (P03). Neither raises false alarms either.",
        "One run per setting. Sonnet high and Haiku xhigh replicate on the second 500 problems.",
    ],
    "height": 620,
}

EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
# The models whose detection moves most with effort. Haiku and GLM keep their report colours.
MODELS = [("haiku55", "Haiku 5.5", True), ("glm53", "GLM-5.3", True),
          ("luna", "GPT-6 Luna", False), ("qwen38", "Qwen 3.8", False)]
LEVELS = [(0.2, "2 or more"), (0.3, "3 or more"), (0.5, "5 or more")]
INITIAL = 2


def rungs(t, model):
    d = t[(t.model == model) & (t.budget_pct == 2)]
    return {REMAP.get(r.effort, r.effort): r for _, r in d.iterrows()}


def line(sid, name, hot, axis, data, label=True):
    color = entity(sid.split(":")[1]) if hot else "@context-strong"
    return {"id": sid, "name": name, "type": "line", "xAxisIndex": axis, "yAxisIndex": axis, "data": data,
            "connectNulls": True, "z": 4 if hot else 3, "symbolSize": 8 if hot else 6,
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
            "lineStyle": {"color": color, "width": 2.5 if hot else 1.5},
            "endLabel": {"show": label, "formatter": "{a}", "color": "@ink-primary" if hot else "@ink-muted",
                         "fontSize": 12 if hot else 11, "fontWeight": 600 if hot else 400, "distance": 8},
            "labelLayout": {"moveOverlap": "shiftY"}, "emphasis": {"focus": "series"}}


def bars(sid, hot, axis, data):
    color = entity(sid.split(":")[1]) if hot else "@context-strong"
    return {"id": sid, "type": "custom", "renderItem": C.VBAR, "xAxisIndex": axis, "yAxisIndex": axis,
            "itemStyle": {"color": color}, "data": data, "silent": True, "tooltip": {"show": False}, "z": 2}


def build() -> Figure:
    t = S.run_table()
    top, rows, gains = [], [], []
    for model, name, hot in MODELS:
        by = rungs(t, model)
        pts = [by.get(e) for e in EFFORT_ORDER]
        top.append(line(f"top:{model}", name, hot, 0, [
            None if r is None else {"value": round(100 * r.safety_exact, 2),
                                    "tip": f"<b>{r['name']}</b><br>caught {C.pct(r.safety_exact)}% "
                                           f"({C.pct(r.ci_lo)} to {C.pct(r.ci_hi)})"} for r in pts]))
        top.append(bars(f"topci:{model}", hot, 0, [[i, round(100 * r.ci_lo, 2), round(100 * r.ci_hi, 2)]
                                                    for i, r in enumerate(pts) if r is not None]))
        got = [r for r in pts if r is not None]
        gains.append(100 * (got[-1].safety_exact - got[0].safety_exact))

    def bottom(level):
        out = []
        for model, name, hot in MODELS:
            by = rungs(t, model)
            data, ci = [], []
            for i, e in enumerate(EFFORT_ORDER):
                r = by.get(e)
                if r is None:
                    data.append(None)
                    continue
                h, _ = S.load_scores(r.run)
                k, n = int((h >= level).sum()), len(h)
                lo, hi = S.wilson(k, n)
                data.append({"value": round(100 * k / n, 2),
                             "tip": f"<b>{r['name']}</b><br>{k} of {n} clean programs scored "
                                    f"{level * 10:g}/10 or more ({100 * k / n:.1f}%)"})
                ci.append([i, round(100 * lo, 2), round(100 * hi, 2)])
                rows.append({"model": name, "effort": e, "run": r.run, "level": level, "clean_flagged": k,
                             "n_clean": n, "caught_at_2pct": r.safety_exact})
            out.append(line(f"bot:{model}", name, hot, 1, data, label=False))  # named in the top panel
            out.append(bars(f"botci:{model}", hot, 1, ci))
        return out

    frames = [{"series": top + bottom(level)} for level, _ in LEVELS]
    x = {"type": "category", "boundaryGap": False, "data": EFFORT_LABEL}
    option = C.base(
        grid=[{"left": 64, "right": 120, "top": 16, "height": "48%"},
              {"left": 64, "right": 120, "bottom": 52, "height": "27%"}],
        xAxis=[{**x, "axisLabel": {"show": False}}, C.axis("Reasoning effort setting", gridIndex=1, **x)],
        yAxis=[C.axis("Backdoors caught", gap=46, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
               C.axis("Clean flagged", gap=46, type="value", gridIndex=1, min=0, max=5, interval=2.5,
                      axisLabel={"formatter": "{value}%"})],
        series=frames[INITIAL]["series"],
    )
    option["animation"] = True
    option["animationDurationUpdate"] = 600
    n_clean = int(len(S.load_scores(S.SONNET)[0]))
    return Figure(option=option, data=rows, facts={"n_clean": n_clean, "max_gain": max(gains)},
                  dial={"label": "Counts as a false alarm (score out of 10)", "steps": [s for _, s in LEVELS],
                        "initial": INITIAL, "frames": frames})
