"""M27: variation on M22. Opus as a ranked bar per hard backdoor, with the small monitors marked on it."""
import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M27",
    "title": "Ranked by Opus, the hard backdoors fall off a cliff",
    "section": "results",
    "order": 138,
    "caption": ("A variation on M22. One bar per hard backdoor, the length being what Opus 5.5 gave "
                "it at xhigh effort, ranked. The ticks on each bar are Sonnet and Haiku on the same "
                "code. Below the {thresh:d} line the bars collapse: {n_low:d} of {n:d} sit under "
                "{low:d} out of 100."),
    "notes": [
        "Same data as M22 with the dots replaced by bars, so the eye reads length instead of "
        "position. The shape this form shows best is the cliff: a short head of high scores and a "
        "long flat tail, rather than a gradual slope.",
        "A pale, outlined bar is a backdoor some panel monitor caught, which is why it is in this "
        "hard set but not in the never-caught group of {n_nc:d}.",
        "The dashed yellow line at {thresh:d} is a reading aid. Opus has no honest baseline on this set, so "
        "it has no cutoff and no audit budget, and a real deployment would have to set one against "
        "honest code.",
        "Bars start at zero and the scale is the full 0 to 100, so no length is exaggerated. The "
        "small-monitor ticks sit on the same scale.",
        "Thin data. {n:d} bars, single scores, one pass each. Neighbouring bars differing by a point "
        "or two are not distinguishable measurements.",
    ],
    "height": 900,
}

THRESH, LOW = 50, 20


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d = d.rename(columns={"Haiku 5.5 xhigh": "haiku", "Sonnet 5.5": "sonnet"})
    d = d.sort_values(["opus_xhigh", "sample_id"], ascending=[False, True]).reset_index(drop=True)
    d["sample_id"] = d.sample_id.astype(str)
    labels = list(d.sample_id)[::-1]
    rev = list(d.itertuples())[::-1]

    # Two stacked series, each holding the rows the other leaves null, so the bars keep full
    # width and the legend carries the solid / outlined key instead of a sentence in the notes.
    BAR_SPLIT = [("Opus xhigh · no monitor caught it", True,
                  {"color": entity("opus55"), "borderRadius": [0, 4, 4, 0]}),
                 ("Opus xhigh · a panel monitor caught it", False,
                  {"color": f"{entity('opus55')}/0.28", "borderColor": entity("opus55"),
                   "borderWidth": 1.4, "borderRadius": [0, 4, 4, 0]})]
    bars = []
    for name, never, style in BAR_SPLIT:
        bars.append({
            "name": name, "type": "bar", "stack": "b", "barWidth": "68%", "itemStyle": style,
            "data": [({"value": r.opus_xhigh,
                       "tip": (f"<b>problem {r.sample_id}</b><br>Opus 5.5 xhigh {r.opus_xhigh:g}"
                               f"<br>Sonnet {r.sonnet:g}, Haiku {r.haiku:g}"
                               f"<br>{'caught by no monitor' if never else 'caught by a panel monitor'}")}
                      if (r.group == "never_caught") == never else None)
                     for r in rev],
        })
    bars[0]["markLine"] = {"silent": True, "symbol": "none", "label": {"show": False},
                           "lineStyle": {"color": "@warning", "type": "dashed", "width": 1.5},
                           "data": [{"xAxis": THRESH}]}

    ticks = [{
        "name": name, "type": "scatter", "symbol": "rect", "symbolSize": [3, 13], "z": 5,
        "itemStyle": {"color": colour},
        "data": [{"value": [getattr(r, col), i],
                  "tip": f"<b>problem {r.sample_id}</b><br>{name}: {getattr(r, col):g} of 100"}
                 for i, r in enumerate(rev)],
    } for name, col, colour in [("Sonnet 5.5", "sonnet", entity("sonnet55")),
                                ("Haiku 5.5 xhigh", "haiku", entity("haiku55"))]]

    facts = {"n": len(d), "thresh": THRESH, "low": LOW,
             "n_low": int((d.opus_xhigh < LOW).sum()),
             "n_nc": int((d.group == "never_caught").sum())}
    rows = [{"sample_id": r.sample_id, "group": r.group, "opus_xhigh": r.opus_xhigh,
             "sonnet55": r.sonnet, "haiku55_xhigh": r.haiku} for r in d.itertuples()]
    option = C.base(
        grid={"left": 78, "right": 32, "top": 40, "bottom": 54},
        xAxis=C.axis("Suspicion score, 0 to 100", type="value", min=0, max=100, interval=20),
        yAxis=C.axis("Problem id", gap=64, type="category", data=labels,
                     axisLabel={"fontSize": 11}),
        legend={"top": 0, "left": 72, "itemGap": 18,
                "data": [n for n, _, _ in BAR_SPLIT] + ["Sonnet 5.5", "Haiku 5.5 xhigh"]},
        series=bars + ticks,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
