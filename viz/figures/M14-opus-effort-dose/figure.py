"""M14: Opus 5.5's score on each hard backdoor at low effort against the same backdoor at xhigh."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M14",
    "title": "Most backdoors score the same at low and xhigh effort",
    "section": "appendix",
    "order": 122,
    "caption": ("One mark per backdoor: Opus 5.5's score at low effort across, the same backdoor at xhigh "
                "effort up. The diagonal is no change, so a mark above it means more thinking raised the "
                "score. Colour is whether any small monitor caught that backdoor."),
    "notes": [
        "{moved:d} of {n_both:d} move by {step:d} points or more between the two efforts, {up:d} up and "
        "{down:d} down. More thinking mostly confirms the first answer rather than changing it.",
        "{n_see:d} backdoors go from near zero at low effort to {high_mark:d} or above at xhigh, which is "
        "where the extra effort earns its cost.",
        "Cost per call is not in this figure. It comes from the monitor's token usage, which lives in "
        "gitignored eval logs rather than a committed CSV, so the source figure's price comparison is left "
        "out rather than typed in by hand.",
        "Ported from scripts/analysis_opus_hard51.py, which drew this as opus-hard51-fig3-effort.png.",
    ],
    "height": 560,
}

GROUPS = [("never_caught", "Missed by every monitor", "@s7"),
          ("caught_at_0to100", "Caught by Sonnet or Haiku", "@context-strong")]
LO, HI, STEP, HIGH = "opus_low", "opus_xhigh", 10, 50


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d49 = d[d.group.isin([g for g, _, _ in GROUPS])].dropna(subset=[HI])
    series = [{
        "name": "no change", "type": "line", "symbol": "none", "silent": True,
        "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1.5},
        "data": [[0, 0], [100, 100]], "tooltip": {"show": False},
    }]
    rows = []
    for key, label, color in GROUPS:
        g = d49[d49.group == key]
        series.append({
            "name": label, "type": "scatter", "symbolSize": 11,
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.2},
            "data": [{"value": [float(max(r[LO], 0)), float(max(r[HI], 0))],
                      "tip": (f"<b>Problem {int(r.sample_id)}</b><br>{label}"
                              f"<br>low: {r[LO]:g}<br>xhigh: {r[HI]:g}")}
                     for _, r in g.iterrows()],
        })
        rows += [{"sample_id": int(r.sample_id), "group": label,
                  "opus_low": float(r[LO]), "opus_xhigh": float(r[HI])} for _, r in g.iterrows()]
    both = d49[[LO, HI]].dropna()
    diff = both[HI] - both[LO]
    facts = {"n_both": len(both), "moved": int((diff.abs() >= STEP).sum()), "step": STEP,
             "up": int((diff >= STEP).sum()), "down": int((diff <= -STEP).sum()),
             "n_see": int(((d49[LO] <= 5) & (d49[HI] >= HIGH)).sum()), "high_mark": HIGH}
    option = C.base(
        grid={"left": 72, "right": 32, "top": 46, "bottom": 60},
        xAxis=C.axis("Opus score at low effort", type="value", min=0, max=100),
        yAxis=C.axis("Opus score at xhigh effort", gap=50, type="value", min=0, max=100),
        legend={"top": 0, "left": 66, "data": [l for _, l, _ in GROUPS]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts)
