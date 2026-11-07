"""A06: as reasoning effort rises, catches go up (top) while false alarms on clean code stay flat (bottom)."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "A06",
    "title": "More reasoning catches more backdoors without raising false alarms",
    "section": "appendix",
    "order": 6,
    "caption": ("Top: backdoors caught at a 2% audit budget at each reasoning setting, with 95% intervals. "
                "Bottom: share of the {n_clean} clean programs the same monitors score 5/10 or higher. "
                "Detection rises by up to {max_gain:.0f} points while false alarms stay near zero."),
    "notes": [],
    "height": 560,
}

EFFORT_ORDER = ["off", "low", "medium", "high", "xhigh"]
EFFORT_LABEL = ["off", "low", "medium", "high", "xhigh"]
MODELS = [("luna", "GPT-6 Luna", "@s6"), ("qwen38", "Qwen 3.8", "@s4")]
LEVEL = 0.5   # a score of 5/10 or more counts as a false alarm


def line(sid, name, color, axis, data, label):
    return {"id": sid, "name": name, "type": "line", "xAxisIndex": axis, "yAxisIndex": axis, "data": data,
            "connectNulls": True, "z": 4, "symbolSize": 8,
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
            "lineStyle": {"color": color, "width": 2.5},
            "endLabel": {"show": label, "formatter": "{a}", "color": "@ink-primary", "fontSize": 12,
                         "fontWeight": 600, "distance": 8},
            "labelLayout": {"moveOverlap": "shiftY"}, "emphasis": {"focus": "series"}}


def bars(sid, color, axis, data):
    return {"id": sid, "type": "custom", "renderItem": C.VBAR, "xAxisIndex": axis, "yAxisIndex": axis,
            "itemStyle": {"color": color}, "data": data, "silent": True, "tooltip": {"show": False}, "z": 2}


def build() -> Figure:
    t = S.run_table()
    series, rows, gains = [], [], []
    for model, name, color in MODELS:
        d = t[(t.model == model) & (t.budget_pct == 2)]
        by = {r.effort: r for _, r in d.iterrows()}
        pts = [by.get(e) for e in EFFORT_ORDER]
        top, top_ci, bot, bot_ci = [], [], [], []
        for i, r in enumerate(pts):
            if r is None:
                top.append(None); bot.append(None)
                continue
            h, _ = S.load_scores(r.run)
            k, n = int((h >= LEVEL).sum()), len(h)
            lo, hi = S.wilson(k, n)
            top.append({"value": round(100 * r.safety_exact, 2),
                        "tip": f"<b>{r['name']}</b><br>caught {C.pct(r.safety_exact)}% ({C.pct(r.ci_lo)} to {C.pct(r.ci_hi)})"})
            top_ci.append([i, round(100 * r.ci_lo, 2), round(100 * r.ci_hi, 2)])
            bot.append({"value": round(100 * k / n, 2),
                        "tip": f"<b>{r['name']}</b><br>{k} of {n} clean programs scored 5/10 or more"})
            bot_ci.append([i, round(100 * lo, 2), round(100 * hi, 2)])
            rows.append({"model": name, "effort": r.effort, "run": r.run, "caught_at_2pct": r.safety_exact,
                         "clean_flagged_5of10": k, "n_clean": n})
        got = [r for r in pts if r is not None]
        gains.append(100 * (got[-1].safety_exact - got[0].safety_exact))
        series += [line(f"top:{model}", name, color, 0, top, True), bars(f"topci:{model}", color, 0, top_ci),
                   line(f"bot:{model}", name, color, 1, bot, False), bars(f"botci:{model}", color, 1, bot_ci)]

    x = {"type": "category", "boundaryGap": False, "data": EFFORT_LABEL}
    option = C.base(
        grid=[{"left": 64, "right": 110, "top": 16, "height": "50%"},
              {"left": 64, "right": 110, "bottom": 52, "height": "24%"}],
        xAxis=[{**x, "axisLabel": {"show": False}}, C.axis("Reasoning effort setting", gridIndex=1, **x)],
        yAxis=[C.axis("Backdoors caught", gap=46, type="value", min=0, max=100, axisLabel={"formatter": "{value}%"}),
               C.axis("Clean flagged", gap=46, type="value", gridIndex=1, min=0, max=5, interval=2.5,
                      axisLabel={"formatter": "{value}%"})],
        series=series,
    )
    n_clean = int(len(S.load_scores(S.SONNET)[0]))
    return Figure(option=option, data=rows, facts={"n_clean": n_clean, "max_gain": max(gains)})
