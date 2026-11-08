"""M12: Opus 5.5's score on the 49 hard backdoors, split by whether any small monitor caught them."""
import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M12",
    "title": "Opus agrees with the small monitors about which backdoors look obvious",
    "section": "appendix",
    "order": 120,
    "caption": ("One mark per backdoor, spread sideways so they do not overlap; height is Opus 5.5's "
                "suspicion score at xhigh effort. The thick line in each group is its median. The groups "
                "come from what Sonnet and Haiku did, so Opus had no part in making them."),
    "notes": [
        "Backdoors that Sonnet or Haiku caught get a median Opus score of {med_caught:g}. The ones every "
        "monitor missed get {med_missed:g}. Opus ranks them the same way the small monitors do.",
        "Opus never saw honest code in this experiment, so these scores rank backdoors and are not a catch "
        "rate. Where its audit cutoff would sit is unknown.",
        "The {n_missed:d} missed and {n_caught:d} caught backdoors here are the two groups of the 51 hard "
        "set that every monitor scored on the 0 to 100 prompt; the {n_other:d} caught only by a 0 to 10 "
        "Haiku run are left out, as in the source figure.",
        "Ported from scripts/analysis_opus_hard51.py, which drew this as opus-hard51-fig1-agreement.png.",
    ],
    "height": 520,
}

GROUPS = [("never_caught", "Missed by every monitor", "@s7"),
          ("caught_at_0to100", "Caught by Sonnet or Haiku", "@context-strong")]
COL = "opus_xhigh"


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d49 = d[d.group.isin([g for g, _, _ in GROUPS])].dropna(subset=[COL])
    rng = np.random.default_rng(3)          # fixed, so a rebuild puts every mark back where it was
    series, rows, facts, ticks = [], [], {}, []
    for i, (key, label, color) in enumerate(GROUPS):
        g = d49[d49.group == key]
        jitter = rng.uniform(-0.15, 0.15, len(g))
        series.append({
            "name": label, "type": "scatter", "symbolSize": 11,
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.2},
            "data": [{"value": [round(i + j, 4), float(max(v, 0))],
                      "tip": f"<b>Problem {sid}</b><br>{label}<br>Opus xhigh: {v:g}"}
                     for j, v, sid in zip(jitter, g[COL], g.sample_id)],
        })
        med = float(g[COL].median())
        series.append({
            "name": f"{label} median", "type": "line", "symbol": "none", "silent": True,
            "lineStyle": {"color": "@ink-primary", "width": 3},
            "data": [[i - 0.32, med], [i + 0.32, med]],
            "endLabel": {"show": True, "formatter": f"median {med:g}", "color": "@ink-primary",
                         "fontSize": 12, "offset": [6, 0]},
            "tooltip": {"show": False},
        })
        ticks.append(label)
        rows += [{"sample_id": sid, "group": label, "opus_xhigh": float(v)}
                 for sid, v in zip(g.sample_id, g[COL])]
        facts[f"med_{'missed' if key == 'never_caught' else 'caught'}"] = med
        facts[f"n_{'missed' if key == 'never_caught' else 'caught'}"] = len(g)
    facts["n_other"] = int((d.group == "caught_at_0to10_only").sum())
    option = C.base(
        grid={"left": 76, "right": 150, "top": 46, "bottom": 36},
        xAxis=C.axis("", type="value", min=-0.6, max=1.75, splitLine={"show": False},
                     axisLabel={"show": False}, axisTick={"show": False}),
        yAxis=C.axis("Opus 5.5 suspicion score", gap=52, type="value", min=0, max=100),
        legend={"top": 0, "left": 70, "data": ticks},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts)
