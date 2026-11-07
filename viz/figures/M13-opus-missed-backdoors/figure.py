"""M13: the highest Opus 5.5 scores among the backdoors no small monitor caught."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M13",
    "title": "{n20} of {n_missed} backdoors no monitor caught look suspicious to Opus",
    "section": "appendix",
    "order": 121,
    "caption": ("The ten highest-scored backdoors among the {n_missed:d} that no monitor caught. Bars are "
                "Opus 5.5 at xhigh effort. Each row label is the problem id and, in brackets, what Sonnet "
                "and Haiku gave the same backdoor. Those two never go above {small_max:g} on any of them."),
    "notes": [
        "Opus scores the other {n_rest:d} missed backdoors at {rest_max:g} or below, median {rest_med:g}, "
        "so this is a tail rather than a general advantage.",
        "Opus never saw honest code here, so a high score is not a catch. Without its own honest "
        "distribution there is no cutoff to compare these against.",
        "P12 carries this finding in the report as a share of the whole set. This figure is the per-backdoor "
        "detail behind it, kept in the appendix.",
        "Ported from scripts/analysis_opus_hard51.py, which drew this as opus-hard51-fig2-missed.png.",
    ],
    "height": 520,
}

COL = "opus_xhigh"
THRESH = 20


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    miss = d[d.group == "never_caught"].dropna(subset=[COL])
    # Ties broken by problem id so every machine builds the same order.
    top = miss.sort_values([COL, "sample_id"], ascending=[False, True], kind="stable").head(10).iloc[::-1]
    rest = miss.drop(top.index)
    labels = [f"{int(r.sample_id)}  ({r['Sonnet 5.5']:g} / {r['Haiku 5.5 xhigh']:g})" for _, r in top.iterrows()]
    option = C.base(
        grid={"left": 150, "right": 64, "top": 20, "bottom": 56},
        xAxis=C.axis("Opus 5.5 suspicion score", type="value", min=0, max=100),
        yAxis=C.axis("", type="category", data=labels, gap=10,
                     axisTick={"show": False}, splitLine={"show": False}),
        series=[{
            "name": "Opus 5.5 · xhigh", "type": "bar", "barWidth": "55%",
            "itemStyle": {"color": "@s7", "borderRadius": [0, 5, 5, 0]},
            "label": {"show": True, "position": "right", "color": "@ink-primary",
                      "fontWeight": 600, "fontSize": 12, "formatter": "{c}"},
            "data": [{"value": float(r[COL]),
                      "tip": (f"<b>Problem {int(r.sample_id)}</b><br>Opus xhigh: {r[COL]:g}"
                              f"<br>Sonnet 5.5: {r['Sonnet 5.5']:g}"
                              f"<br>Haiku 5.5 xhigh: {r['Haiku 5.5 xhigh']:g}")}
                     for _, r in top.iterrows()],
        }],
    )
    rows = [{"sample_id": int(r.sample_id), "opus_xhigh": float(r[COL]),
             "sonnet55": float(r["Sonnet 5.5"]), "haiku55_xhigh": float(r["Haiku 5.5 xhigh"])}
            for _, r in top.iterrows()]
    facts = {"n_missed": len(miss), "n20": int((miss[COL] >= THRESH).sum()), "thresh": THRESH,
             "n_rest": len(rest), "rest_max": float(rest[COL].max()), "rest_med": float(rest[COL].median()),
             "small_max": float(max(miss["Sonnet 5.5"].max(), miss["Haiku 5.5 xhigh"].max()))}
    return Figure(option=option, data=rows, facts=facts)
