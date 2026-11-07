"""M07: how well reasoning length separates backdoors, against how well the suspicion score does."""
import glob

import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M07",
    "title": "Thinking length only beats the score where the score has collapsed",
    "section": "appendix",
    "order": 137,
    "caption": ("One dot per run that emits hidden reasoning: how well the suspicion score separates "
                "backdoored from clean programs across, how well the number of reasoning tokens does it "
                "up. Both are areas under the ROC curve, where a half is a coin flip. Above the diagonal, "
                "length is the better signal."),
    "notes": [
        "Length wins in {n_win} of {n} runs and loses in {n_lose}. The winners are not a random subset: "
        "their suspicion AUC runs {w_lo} to {w_hi}, the bottom of the study. Length rescues a collapsed "
        "score rather than beating a working one.",
        "The best-separating arms are far from the diagonal in the other direction. The score is a much "
        "stronger signal exactly where the monitor is any good, so this is not a free second opinion.",
        "A monitor that does not reason has no tie-break available at all, so runs reporting no tokens "
        "are left out. A zero can mean the model did not think or that the tokens were never recorded, "
        "and those two are not distinguishable from the committed tables.",
        "Length is cheap in the sense that it is already paid for, but M20 shows how large that payment "
        "is: on some runs the hidden reasoning is most of the bill.",
        "Rebuilt from committed per-sample tables, replacing the exported snapshot. The AUC is the "
        "Mann-Whitney statistic with midranks, the same one scripts/analysis_reasoning_tokens.py uses.",
    ],
    "height": 540,
}


def auc(honest: np.ndarray, attack: np.ndarray) -> float:
    """P(a random attack scores above a random honest one), ties counted as half."""
    x = np.concatenate([attack, honest])
    r = pd.Series(x).rank(method="average").to_numpy()
    return float((r[:len(attack)].sum() - len(attack) * (len(attack) + 1) / 2)
                 / (len(attack) * len(honest)))


def build() -> Figure:
    rows = []
    for p in sorted(glob.glob("results/*-samples.csv")):
        run = p.split("/")[-1][: -len("-samples.csv")]
        d = pd.read_csv(p)
        if "reasoning_tokens" not in d.columns:
            continue
        h, a = d[d["mode"] == "honest"], d[d["mode"] == "attack"]
        if len(h) == 0 or len(a) == 0 or d.reasoning_tokens.fillna(0).sum() <= 0:
            continue
        rows.append({
            "run": run, "label": S.run_label(run),
            "auc_score": auc(h.suspicion.fillna(0).to_numpy(float), a.suspicion.fillna(0).to_numpy(float)),
            "auc_tokens": auc(h.reasoning_tokens.fillna(0).to_numpy(float),
                              a.reasoning_tokens.fillna(0).to_numpy(float))})
    t = pd.DataFrame(rows)
    t["wins"] = t.auc_tokens > t.auc_score
    lo = float(min(t.auc_score.min(), t.auc_tokens.min())) - 0.03
    series = [{"name": "equal", "type": "line", "symbol": "none", "silent": True,
               "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1.5},
               "data": [[lo, lo], [1, 1]], "tooltip": {"show": False}}]
    for wins, name, color in ((True, "length separates better", "@s0"),
                              (False, "the score separates better", "@context-strong")):
        g = t[t.wins == wins]
        series.append({
            "name": name, "type": "scatter", "symbolSize": 11,
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.2},
            "data": [{"value": [round(r.auc_score, 4), round(r.auc_tokens, 4)],
                      "tip": (f"<b>{r.label}</b><br>score AUC {r.auc_score:.3f}"
                              f"<br>length AUC {r.auc_tokens:.3f}")} for r in g.itertuples()]})
    win = t[t.wins]
    facts = {"n": len(t), "n_win": int(t.wins.sum()), "n_lose": int((~t.wins).sum()),
             "w_lo": round(float(win.auc_score.min()), 3), "w_hi": round(float(win.auc_score.max()), 3)}
    option = C.base(
        grid={"left": 76, "right": 32, "top": 40, "bottom": 58},
        xAxis=C.axis("Suspicion score, area under the ROC curve", type="value", min=round(lo, 2), max=1),
        yAxis=C.axis("Reasoning length, same measure", gap=52, type="value", min=round(lo, 2), max=1),
        legend={"top": 0, "left": 70, "data": ["length separates better", "the score separates better"]},
        series=series,
    )
    data = [{"run": r.run, "monitor": r.label, "auc_suspicion": round(r.auc_score, 4),
             "auc_reasoning_tokens": round(r.auc_tokens, 4), "length_wins": bool(r.wins)}
            for r in t.itertuples()]
    return Figure(option=option, data=data, facts=facts)
