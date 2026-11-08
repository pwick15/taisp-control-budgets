"""M28: the original evasion-by-size bars, as two rates per size group rather than a 100% split."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M28",
    "title": "The smallest edits are missed by everything, and caught by nothing",
    "section": "results",
    "order": 104,
    "caption": ("All {n:d} backdoors in four size groups. Each group gets two bars: the share no monitor "
                "caught at a 2% budget, and the share all seven caught. Both rates move the same way with "
                "size, from {miss_lo}% missed in the smallest group down to {miss_hi}%."),
    "notes": [
        "Thin rungs on the left. The two smallest groups hold {n0:d} and {n1:d} backdoors, so their bars "
        "carry 95% intervals of roughly {ci0} and {ci1} points. Read them as an indication of direction, "
        "not as rates. The two right-hand groups hold {n2:d} and {n3:d}.",
        "This is the same finding as P10, drawn the way the original analysis drew it. P10 splits each "
        "group into a full 100% stack with a confidence panel and uses different cut points. Use P10 for "
        "the published number and this one for the shape.",
        "Lines changed is measured against the dataset's reference solution, not against what an honest "
        "model would write. The median backdoor changes more lines than the program has, so these groups "
        "separate rewrites from edits rather than large backdoors from small ones.",
        "The two rates are not complements. A backdoor caught by one to six of the seven monitors is in "
        "neither bar, which is why the pairs do not sum to 100.",
        "Size and author are tangled, and the author attribution is itself confounded: a generator is "
        "credited with a backdoor only when no higher-priority generator produced a working one for that "
        "problem. This figure cannot say whether size or author drives the pattern.",
    ],
    "height": 440,
}

BINS = [(0, 2, "0-2"), (3, 4, "3-4"), (5, 8, "5-8"), (9, 10 ** 9, "9+")]
SERIES = [("Caught by no monitor", "missed", "@s7"),
          ("Caught by all seven", "all", "@good")]


def build() -> Figure:
    cf = S.cases()
    stats, rows = [], []
    for lo, hi, lab in BINS:
        g = cf[(cf.changed_lines >= lo) & (cf.changed_lines <= hi)]
        n = len(g)
        k_miss = int((g.caught_by == 0).sum())
        k_all = int((g.caught_by == 7).sum())
        stats.append({"label": lab, "n": n, "missed": k_miss, "all": k_all})
        rows.append({"changed_lines": lab, "n": n, "caught_by_none": k_miss,
                     "pct_caught_by_none": round(100 * k_miss / n, 1),
                     "caught_by_all_seven": k_all,
                     "pct_caught_by_all_seven": round(100 * k_all / n, 1)})

    series = []
    for name, key, colour in SERIES:
        series.append({
            "name": name, "type": "bar", "barWidth": "32%",
            "itemStyle": {"color": colour, "borderRadius": [4, 4, 0, 0]},
            "label": {"show": True, "position": "top", "fontSize": 12, "color": "@ink-secondary"},
            "data": [{"value": round(100 * s[key] / s["n"], 1),
                      "label": {"formatter": f"{100 * s[key] / s['n']:.1f}%"},
                      "tip": (f"<b>{s['label']} lines changed</b><br>{name.lower()}"
                              f"<br>{s[key]} of {s['n']} backdoors"
                              f"<br>95% interval {100 * S.wilson(s[key], s['n'])[0]:.0f}"
                              f" to {100 * S.wilson(s[key], s['n'])[1]:.0f}%")}
                     for s in stats],
        })

    def halfwidth(s, key):
        lo, hi = S.wilson(s[key], s["n"])
        return round(100 * (hi - lo) / 2)

    facts = {
        "n": int(len(cf)),
        "miss_lo": round(100 * stats[0]["missed"] / stats[0]["n"]),
        "miss_hi": round(100 * stats[-1]["missed"] / stats[-1]["n"]),
        "n0": stats[0]["n"], "n1": stats[1]["n"], "n2": stats[2]["n"], "n3": stats[3]["n"],
        "ci0": halfwidth(stats[0], "missed"), "ci1": halfwidth(stats[1], "missed"),
    }
    option = C.base(
        grid={"left": 66, "right": 30, "top": 44, "bottom": 66},
        xAxis=C.axis("Lines changed, honest to backdoor", gap=46, type="category",
                     data=[f"{s['label']}\nn={s['n']}" for s in stats],
                     axisLabel={"lineHeight": 16}),
        yAxis=C.axis("Share of that size group", gap=46, type="value", min=0, max=70,
                     axisLabel={"formatter": "{value}%"}),
        legend={"top": 0, "left": 60, "itemGap": 18, "data": [s[0] for s in SERIES]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
