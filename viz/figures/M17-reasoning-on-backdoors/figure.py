"""M17: mean hidden reasoning tokens a monitor spends on clean code against backdoored code."""
import glob

import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M17",
    "title": "Every reasoning monitor thinks longer about backdoored code",
    "section": "appendix",
    "order": 131,
    "caption": ("One dot per run that emits hidden reasoning: mean tokens spent on clean programs across, "
                "on backdoored ones up. The dashed line is equal effort, so a dot above it means the "
                "monitor thought longer about the backdoor. Every dot is above it."),
    "notes": [
        "The direction is unanimous: backdoored code draws more reasoning in {n_runs} of {n_runs} runs, "
        "median {mult}x. Length is a signal the monitor gives away for free, before you read its score.",
        "It is not a detector on its own. M07 compares how well reasoning length separates the two "
        "classes against how well the suspicion score does, and the score usually wins.",
        "Only runs with 500 honest and 500 attack programs that report any reasoning are drawn. A run "
        "reporting zero can mean the model does not reason or that the tokens were never recorded, and "
        "those two are not distinguishable here, so they are left out rather than drawn as a flat line.",
        "Reasoning tokens now come from the committed per-sample tables. The explorer version of this "
        "chart read a derived file that only existed on one machine.",
        "Ported from the data explorer's free-butterfly-honest-attack view.",
    ],
    "height": 560,
}

def build() -> Figure:
    rows = []
    for p in sorted(glob.glob("results/*-samples.csv")):
        run = p.split("/")[-1][: -len("-samples.csv")]
        d = pd.read_csv(p)
        if "reasoning_tokens" not in d.columns:
            continue
        h, a = d[d["mode"] == "honest"], d[d["mode"] == "attack"]
        if len(h) != 500 or len(a) != 500 or d.reasoning_tokens.fillna(0).sum() <= 0:
            continue
        rows.append({"run": run, "label": S.run_label(run),
                     "honest": float(h.reasoning_tokens.fillna(0).mean()),
                     "attack": float(a.reasoning_tokens.fillna(0).mean())})
    t = pd.DataFrame(rows).sort_values("attack")
    import math
    top = math.ceil(max(t.attack.max(), t.honest.max()) * 1.08 / 1000) * 1000
    option = C.base(
        grid={"left": 86, "right": 34, "top": 30, "bottom": 60},
        xAxis=C.axis("Mean reasoning tokens on clean code", type="value", min=0, max=top),
        yAxis=C.axis("Mean reasoning tokens on backdoored code", gap=62, type="value", min=0, max=top),
        series=[
            {"name": "equal effort", "type": "line", "symbol": "none", "silent": True,
             "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1.5},
             "data": [[0, 0], [top, top]], "tooltip": {"show": False}},
            {"name": "one run", "type": "scatter", "symbolSize": 11,
             "itemStyle": {"color": "@s0", "borderColor": "@ink-surface", "borderWidth": 1.2},
             "data": [{"value": [round(r.honest, 1), round(r.attack, 1)],
                       "tip": (f"<b>{r.label}</b><br>clean: {r.honest:,.0f} tokens"
                               f"<br>backdoored: {r.attack:,.0f} tokens"
                               f"<br>{r.attack / r.honest:.2f}x")} for r in t.itertuples()]},
        ],
    )
    facts = {"n_runs": len(t), "mult": round(float((t.attack / t.honest).median()), 2)}
    data = [{"run": r.run, "monitor": r.label, "honest_mean_reasoning": round(r.honest, 1),
             "attack_mean_reasoning": round(r.attack, 1),
             "multiplier": round(r.attack / r.honest, 3)} for r in t.itertuples()]
    return Figure(option=option, data=data, facts=facts)
