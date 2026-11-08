"""M05: does reading comments still help once the threshold is set on honest code that has comments?"""
import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M05",
    "title": "Calibrating on commented honest code widens the comment advantage",
    "section": "appendix",
    "order": 139,
    "caption": ("Backdoors caught against honest programs audited, for a monitor reading code with "
                "comments and the same monitor reading it stripped. Filled marks set the cutoff on bare "
                "honest code, hollow marks on honest code that carries comments. Diamonds mark where a "
                "{budget}% request lands."),
    "notes": [
        "The objection this answers: a monitor that reads comments scores everything higher, so it may "
        "only look better because its threshold was borrowed from a stripped run. Give it its own honest "
        "distribution and the advantage does not shrink. It grows, from {gap_bare} points to {gap_cmt}.",
        "Calibrated on commented honest code the two arms catch {k_cmt}% and {s_cmt}%; on bare honest "
        "code, {k_bare}% and {s_bare}%. Both arms fall when the cutoff is fairer, and the stripped one "
        "falls further.",
        "Data quality: a {budget}% request serves {served_cmt}% on the commented control, because the "
        "honest scores are coarse and the cutoff snaps down. The diamonds sit where the request actually "
        "lands, not where it was asked for.",
        "Honest programs with short and with long comments give the same cutoff here, so only one "
        "commented calibration is drawn. The scores are discrete enough that extra comment length moves "
        "nothing.",
        "Both experiments call the monitor directly rather than through the eval harness, so these "
        "numbers are not joinable to the run tables and are not meant to be.",
    ],
    "height": 540,
}

BUDGET = 2
ARMS = [("comments kept", "kept", "@s0"), ("comments stripped", "stripped", "@s1")]
CALS = [("bare honest code", "bare", False), ("commented honest code", "short", True)]
XMAX = 6.0


def curve(honest: np.ndarray, attack: np.ndarray) -> list[tuple[float, float]]:
    pts = []
    for v in np.unique(honest):
        f = 100 * float((honest > v).mean())
        if 0 < f <= XMAX:
            pts.append((f, float((attack > v).mean())))
    return sorted(pts)


def build() -> Figure:
    cl = pd.read_csv(S.ANALYSIS / "comment-length.csv").dropna(subset=["bare", "short", "long"])
    hc = pd.read_csv(S.ANALYSIS / "honest-calibration.csv").dropna(subset=["kept", "stripped"])
    series, rows, facts = [], [], {"budget": BUDGET}
    marks = []
    for cal_name, cal_col, hollow in CALS:
        h = cl[cal_col].to_numpy(float)
        thr = float(np.percentile(h, 100 - BUDGET))
        served = 100 * float((h > thr).mean())
        tag = "cmt" if hollow else "bare"
        for arm_name, arm_col, color in ARMS:
            a = hc[arm_col].to_numpy(float)
            pts = curve(h, a)
            series.append({
                "name": f"{arm_name}, {cal_name.split()[0]} cutoff", "type": "line",
                "symbolSize": 9, "lineStyle": {"color": color, "width": 2.2},
                "itemStyle": {"color": "@ink-surface" if hollow else color,
                              "borderColor": color, "borderWidth": 2 if hollow else 1.5},
                "data": [{"value": [round(f, 3), round(r, 4)],
                          "tip": (f"<b>{arm_name}</b><br>{cal_name}<br>{f:.2f}% audited"
                                  f"<br>{100 * r:.1f}% of backdoors caught")} for f, r in pts]})
            rec = float((a > thr).mean())
            facts[f"{'k' if arm_col == 'kept' else 's'}_{tag}"] = round(100 * rec, 1)
            marks.append((served, rec, arm_name, cal_name))
            rows += [{"arm": arm_name, "calibration": cal_name, "fpr_pct": round(f, 3),
                      "caught": round(r, 4)} for f, r in pts]
        facts[f"served_{tag}"] = round(served, 2)
    facts["gap_bare"] = round(facts["k_bare"] - facts["s_bare"], 1)
    facts["gap_cmt"] = round(facts["k_cmt"] - facts["s_cmt"], 1)
    series.append({
        "name": f"where a {BUDGET}% request lands", "type": "scatter", "symbol": "diamond",
        "symbolSize": 20, "z": 1, "itemStyle": {"color": "@warning/0.85"},
        "data": [{"value": [round(s, 3), round(r, 4)],
                  "tip": f"<b>{an}</b><br>{cn}<br>{s:.2f}% audited, {100 * r:.1f}% caught"}
                 for s, r, an, cn in marks]})
    option = C.base(
        grid={"left": 76, "right": 34, "top": 56, "bottom": 58},
        xAxis=C.axis("Honest programs audited", type="value", min=0, max=XMAX,
                     axisLabel={"formatter": "{value}%"}),
        yAxis=C.axis("Backdoors caught", gap=52, type="value", min=0.4, max=1,
                     axisLabel={"formatter": "function (v) { return (v * 100) + '%'; }"}),
        legend={"top": 0, "left": 70, "itemGap": 14,
                "data": [s["name"] for s in series]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts)
