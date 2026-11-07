"""P17: false alarms on clean code at each reasoning setting, all 8 models (pairs with P03)."""
from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P17",
    "title": "More reasoning doesn't raise false alarms on clean code",
    "section": "results",
    "order": 35,
    "caption": ("Share of the 500 clean programs each monitor scores 5/10 or higher, at each reasoning setting. "
                "Coloured lines are the three models in focus, grey the other five. Every model stays between "
                "{lo:.1f}% and {hi:.1f}% at every setting, while P03 shows {n_gain} of 8 catching more backdoors."),
    "notes": [
        "At a fixed audit budget the false-positive rate is fixed by construction: 2% of clean code gets audited "
        "whatever the monitor. This asks a different question: does more reasoning push clean code's scores up? "
        "It doesn't; Haiku 5.5's mean clean score even falls as effort rises.",
        "Extends A06's false-alarm panel from two models to all eight.",
    ],
    "height": 380,
}

EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium / default", "high", "xhigh / max"]
REMAP = {"max": "xhigh", "default": "medium"}
LADDER = {"sonnet55": "Sonnet 5.5", "haiku55": "Haiku 5.5", "glm53": "GLM-5.3", "qwen38": "Qwen 3.8",
          "luna": "GPT-6 Luna", "mistrallarge4": "Mistral Large 4", "gptoss": "gpt-oss-120b",
          "gemini35lite": "Gemini Flash-Lite"}
HOT = ("sonnet55", "haiku55", "glm53")
LEVEL = 0.5   # a clean program scored 5/10 or more counts as a false alarm


def build() -> Figure:
    t = S.run_table()
    d = t[t.budget_pct == 2]
    series, rows, vals, gains = [], [], [], 0
    for model, label in LADDER.items():
        by = {REMAP.get(r.effort, r.effort): r for _, r in d[d.model == model].iterrows()}
        ks = [e for e in EFFORT_ORDER if e in by]
        gains += by[ks[-1]].safety_exact > by[ks[0]].safety_exact
        data = []
        for e in EFFORT_ORDER:
            if e not in by:
                data.append(None)
                continue
            h, _ = S.load_scores(by[e].run)
            n, pct = int((h >= LEVEL).sum()), 100 * float((h >= LEVEL).mean())
            vals.append(pct)
            data.append({"value": round(pct, 2), "tip": f"<b>{by[e]['name']}</b><br>{n} of {len(h)} clean programs scored 5/10 or more"})
            rows.append({"model": label, "effort": by[e].effort, "clean_flagged": n, "clean_total": len(h), "pct": pct})
        hot = model in HOT
        color = entity(model) if hot else "@context-strong"
        series.append({
            "name": label, "type": "line", "data": data, "connectNulls": True, "z": 4 if hot else 3,
            "symbolSize": 8 if hot else 6, "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
            "lineStyle": {"color": color, "width": 2.5 if hot else 1.5},
            "emphasis": {"focus": "series"},
        })
    option = C.base(
        grid={"left": 58, "right": 40, "top": 40, "bottom": 52},
        legend={"top": 0, "left": 50, "data": [LADDER[m] for m in HOT]},
        xAxis=C.axis("Reasoning effort setting", type="category", boundaryGap=False, data=EFFORT_LABEL),
        yAxis=C.axis("Clean programs flagged", gap=44, type="value", min=0, max=3, interval=1,
                     axisLabel={"formatter": "{value}%"}),
        series=series,
    )
    return Figure(option=option, data=rows, facts={"lo": min(vals), "hi": max(vals), "n_gain": int(gains)})
