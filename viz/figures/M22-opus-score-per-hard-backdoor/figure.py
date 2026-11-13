"""M22: every hard backdoor as a row, scored by Opus 5.5 and by the two small monitors."""
import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M22",
    "title": "A handful of these backdoors alarm Opus and nothing else",
    "section": "results",
    "order": 135,
    "caption": ("One row per hard backdoor, {n:d} of them, ordered by Opus 5.5's score at xhigh effort. All "
                "three monitors score 0 to 100. Opus clears {thresh:d} on {n20:d} rows where Sonnet and Haiku "
                "never go above {small_max:g}. Solid Opus dots are backdoors no other monitor caught; hollow "
                "ones, at least one did."),
    "notes": [
        "Hollow means at least one of our seven monitors caught it in some version of the run (on the 0 "
        "to 100 scale, or one Haiku 0 to 10 run). That's why it's in this hard set but not among the "
        "{n_nc:d} nothing caught.",
        "The dashed yellow line is {thresh:d} out of 100. Opus has no honest baseline here, so it has "
        "no cutoff of its own and no audit budget: that line is a reading aid, not an operating "
        "point, and a real deployment would set one against honest code instead.",
        "The ordering is Opus's own, so the chart cannot help but look favourable to Opus at the top. "
        "The comparison that matters is horizontal, within a row, where Sonnet and Haiku had the same "
        "code in front of them.",
        "Sonnet's and Haiku's medians on this set are {son_med:g} and {hai_med:g} out of 100, which is "
        "what being a hard backdoor means: these are the programs our monitors found boring.",
        "Thin data. {n:d} rows is the whole hard set, and the never-caught group inside it is {n_nc:d}. "
        "Single scores, one pass each, no repeat draws, so a row's height is one measurement.",
    ],
    "height": 900,
}

THRESH = 50
SMALL = [("Sonnet 5.5", "sonnet", entity("sonnet55")),
         ("Haiku 5.5 xhigh", "haiku", entity("haiku55"))]


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d = d.rename(columns={"Haiku 5.5 xhigh": "haiku", "Sonnet 5.5": "sonnet"})
    # ties on the Opus score are broken by problem id, so the row order is reproducible
    d = d.sort_values(["opus_xhigh", "sample_id"], ascending=[False, True]).reset_index(drop=True)
    d["sample_id"] = d.sample_id.astype(str)
    labels = list(d.sample_id)[::-1]                        # ECharts category axis runs bottom-up
    y_of = {s: len(d) - 1 - i for i, s in enumerate(d.sample_id)}

    # Opus is split into two series rather than two per-point styles, so the legend itself
    # carries the key: a solid swatch for never caught, a hollow one for caught.
    OPUS_SPLIT = [("Opus · no other monitor caught it", True,
                   {"color": entity("opus55"), "borderColor": "@ink-surface", "borderWidth": 1.2}),
                  ("Opus · another monitor caught it", False,
                   {"color": "@ink-surface", "borderColor": entity("opus55"), "borderWidth": 2})]
    opus = []
    for name, never, style in OPUS_SPLIT:
        g = d[(d.group == "never_caught") == never]
        opus.append({
            "name": name, "type": "scatter", "symbolSize": 11, "z": 4, "itemStyle": style,
            "data": [{"value": [r.opus_xhigh, y_of[r.sample_id]],
                      "tip": (f"<b>problem {r.sample_id}</b><br>Opus 5.5 xhigh: {r.opus_xhigh:g}"
                              f"<br>Sonnet 5.5: {r.sonnet:g}"
                              f"<br>Haiku 5.5 xhigh: {r.haiku:g}"
                              f"<br>{'caught by none of our other monitors' if never else 'caught by at least one of our other monitors'}")}
                     for r in g.itertuples()],
        })

    opus[0]["markLine"] = {"silent": True, "symbol": "none", "label": {"show": False},
                 "lineStyle": {"color": "@warning", "type": "dashed", "width": 1.5},
                 "data": [{"xAxis": THRESH}]}

    series = opus + [{
        "name": name, "type": "scatter", "symbolSize": 8, "z": 3,
        "itemStyle": {"color": colour, "opacity": 0.9,
                      "borderColor": "@ink-surface", "borderWidth": 0.8},
        "data": [{"value": [v, y_of[s]],
                  "tip": f"<b>problem {s}</b><br>{name}: {v:g} of 100"}
                 for s, v in zip(d.sample_id, d[col])],
    } for name, col, colour in SMALL]

    nc = d[d.group == "never_caught"]
    facts = {
        "n": len(d), "n_nc": len(nc), "thresh": THRESH,
        "n20": int((d.opus_xhigh >= THRESH).sum()),
        "small_max": float(d[["sonnet", "haiku"]].max().max()),
        "son_med": float(d.sonnet.median()), "hai_med": float(d.haiku.median()),
    }
    rows = [{"sample_id": r.sample_id, "group": r.group, "opus_xhigh": r.opus_xhigh,
             "opus_low": r.opus_low, "opus_high": r.opus_high, "opus_max": r.opus_max,
             "sonnet55": r.sonnet, "haiku55_xhigh": r.haiku}
            for r in d.itertuples()]
    option = C.base(
        grid={"left": 78, "right": 32, "top": 40, "bottom": 54},
        xAxis=C.axis("Suspicion score, 0 to 100", type="value", min=0, max=100, interval=20),
        yAxis=C.axis("Problem id", gap=64, type="category", data=labels,
             axisLabel={"fontSize": 11}),
        legend={"top": 0, "left": 72, "itemGap": 18,
                "data": [n for n, _, _ in OPUS_SPLIT] + [n for n, _, _ in SMALL]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
