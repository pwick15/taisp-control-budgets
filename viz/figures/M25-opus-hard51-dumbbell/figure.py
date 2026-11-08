"""M25: variation on M22. The Opus gap per hard backdoor, drawn as a span rather than loose dots."""
import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M25",
    "title": "The gap Opus opens over the small monitors, backdoor by backdoor",
    "section": "results",
    "order": 136,
    "caption": ("A variation on M22. One row per hard backdoor. The bar runs from the better of "
                "Sonnet and Haiku to what Opus 5.5 gave the same code at xhigh effort, so its length "
                "is the disagreement. A solid cap means no monitor caught that backdoor. The median "
                "span is {med_gap:g} points."),
    "notes": [
        "Same data and same row order as M22. The difference is that the gap is a length here rather "
        "than a distance your eye has to measure between two dots.",
        "{n_neg:d} of {n:d} rows have Opus at or below the small monitors, so those bars are short or "
        "absent. They are the rows where frontier reasoning adds nothing.",
        "The small end is the better of Sonnet and Haiku, not their average, so the bar is the most "
        "conservative version of the gap. Both of their scores are still in the tooltip and the CSV.",
        "Opus has no honest baseline on this set, so it has no cutoff and no audit budget. A long bar "
        "means Opus found the code more suspicious, not that it would have audited it.",
        "Thin data. {n:d} rows, single scores, one pass each, so a bar is one measurement against one "
        "other measurement.",
    ],
    "height": 900,
}

GAP_C = "@s6/0.35"


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d = d.rename(columns={"Haiku 5.5 xhigh": "haiku", "Sonnet 5.5": "sonnet"})
    d = d.sort_values(["opus_xhigh", "sample_id"], ascending=[False, True]).reset_index(drop=True)
    d["sample_id"] = d.sample_id.astype(str)
    d["small"] = d[["sonnet", "haiku"]].max(axis=1)
    d["gap"] = (d.opus_xhigh - d.small).clip(lower=0)
    labels = list(d.sample_id)[::-1]

    base = {"name": "base", "type": "bar", "stack": "g", "silent": True,
            "itemStyle": {"color": "@ink-surface", "opacity": 0},
            "data": [round(v, 2) for v in d.small][::-1]}
    span = {"name": "Opus above the small monitors", "type": "bar", "stack": "g", "barWidth": 4,
            "itemStyle": {"color": GAP_C},
            "data": [{"value": round(r.gap, 2),
                      "tip": (f"<b>problem {r.sample_id}</b><br>Opus 5.5 xhigh {r.opus_xhigh:g}"
                              f"<br>best small monitor {r.small:g}"
                              f"<br>gap {r.gap:g} points"
                              f"<br>Sonnet {r.sonnet:g}, Haiku {r.haiku:g}")}
                     for r in d.itertuples()][::-1]}

    caps = []
    for name, never, style in [
            ("Opus xhigh · no monitor caught it", True,
             {"color": entity("opus55"), "borderColor": "@ink-surface", "borderWidth": 1.2}),
            ("Opus xhigh · a panel monitor caught it", False,
             {"color": "@ink-surface", "borderColor": entity("opus55"), "borderWidth": 2})]:
        g = d[(d.group == "never_caught") == never]
        caps.append({"name": name, "type": "scatter", "symbolSize": 11, "z": 4, "itemStyle": style,
                     "data": [{"value": [r.opus_xhigh, len(d) - 1 - i],
                               "tip": f"<b>problem {r.sample_id}</b><br>Opus 5.5 xhigh {r.opus_xhigh:g}"}
                              for i, r in zip(g.index, g.itertuples())]})
    small = {"name": "Best of Sonnet and Haiku", "type": "scatter", "symbolSize": 8, "z": 3,
             "itemStyle": {"color": "@context-strong", "borderColor": "@ink-surface", "borderWidth": 0.8},
             "data": [{"value": [r.small, len(d) - 1 - i],
                       "tip": (f"<b>problem {r.sample_id}</b><br>Sonnet {r.sonnet:g}"
                               f"<br>Haiku {r.haiku:g}")}
                      for i, r in enumerate(d.itertuples())]}

    facts = {"n": len(d), "med_gap": float(d.gap.median()),
             "n_neg": int((d.opus_xhigh <= d.small).sum())}
    rows = [{"sample_id": r.sample_id, "group": r.group, "opus_xhigh": r.opus_xhigh,
             "best_small": r.small, "gap": round(r.gap, 2), "sonnet55": r.sonnet,
             "haiku55_xhigh": r.haiku} for r in d.itertuples()]
    option = C.base(
        grid={"left": 78, "right": 32, "top": 40, "bottom": 54},
        xAxis=C.axis("Suspicion score, 0 to 100", type="value", min=0, max=100, interval=20),
        yAxis=C.axis("Problem id", gap=64, type="category", data=labels,
                     axisLabel={"fontSize": 11}),
        legend={"top": 0, "left": 72, "itemGap": 18,
                "data": [c["name"] for c in caps] + [small["name"]]},
        series=[base, span, small] + caps,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
