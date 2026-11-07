"""M23: how many of the hard backdoors Opus scores high, as its reasoning effort is turned up."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M23",
    "title": "More thinking rescues a few more, and still misses most",
    "section": "results",
    "order": 140,
    "caption": ("The {n:d} hard backdoors, counted by what Opus 5.5 scored them at each reasoning "
                "effort. The lower block scored {hi:d} or more out of 100, the upper block {mid:d} to "
                "{hi:d}. Low to xhigh moves the strong block from {lo_hi:d} to {xh_hi:d}."),
    "notes": [
        "Thin rung. The max-effort arm was only run on {n_max:d} of the {n:d} backdoors, so its bar "
        "counts out of {n_max:d} and the other three count out of {n:d}. It is drawn hollow for that "
        "reason and must not be read as the continuation of the ladder.",
        "Even at xhigh, Opus scores {xh_rest:d} of the {n:d} below {mid:d} out of 100. The headline is "
        "the block that is missing, not the block that grows.",
        "Opus has no honest baseline on this set, so {hi:d} and {mid:d} are reading aids rather than "
        "audit thresholds. A real deployment would have to pick a cutoff against honest code, which "
        "would almost certainly sit lower and catch more honest programs with it.",
        "The four arms are the same {n:d} programs at four settings, so the bars are paired rather "
        "than independent samples. The low to xhigh change of {gain:d} programs is {gain} programs, "
        "not a rate, and no interval is attached to it.",
        "Effort names are not comparable across models. Opus xhigh is not Haiku xhigh, and neither "
        "buys a fixed amount of thinking, so this ladder describes Opus only.",
    ],
    "height": 440,
}

HI, MID = 50, 20
EFFORTS = ["low", "high", "xhigh", "max"]


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    n = len(d)
    counts, labels, rows = {}, [], []
    for e in EFFORTS:
        c = d[f"opus_{e}"].dropna()
        hi = int((c >= HI).sum())
        mid = int(((c >= MID) & (c < HI)).sum())
        counts[e] = (hi, mid, len(c))
        labels.append(e if len(c) == n else f"{e} (n={len(c)})")
        rows.append({"effort": e, "scored": len(c), "of": n, f"score_ge_{HI}": hi,
                     f"score_{MID}_to_{HI}": mid, f"score_below_{MID}": len(c) - hi - mid})

    def bar(name, idx, colour):
        return {
            "name": name, "type": "bar", "stack": "s", "barWidth": "46%",
            "itemStyle": {"color": colour, "borderRadius": [0, 0, 0, 0]},
            "data": [{"value": counts[e][idx],
                      "itemStyle": ({"color": "@ink-surface", "borderColor": colour,
                                     "borderWidth": 2} if counts[e][2] != n else {"color": colour}),
                      "tip": (f"<b>Opus 5.5, {e} effort</b><br>{counts[e][idx]} of {counts[e][2]} "
                              f"backdoors<br>{name}"
                              + ("<br>this arm was only run on "
                                 f"{counts[e][2]} of the {n}" if counts[e][2] != n else ""))}
                     for e in EFFORTS],
        }

    facts = {"n": n, "hi": HI, "mid": MID, "lo_hi": counts["low"][0], "xh_hi": counts["xhigh"][0],
             "n_max": counts["max"][2], "xh_rest": n - counts["xhigh"][0] - counts["xhigh"][1],
             "gain": counts["xhigh"][0] - counts["low"][0]}
    option = C.base(
        grid={"left": 68, "right": 30, "top": 40, "bottom": 56},
        xAxis=C.axis("Opus 5.5 reasoning effort", type="category", data=labels),
        yAxis=C.axis(f"Backdoors Opus scores {MID} or more", gap=46, type="value", min=0, max=25, interval=5),
        legend={"top": 0, "left": 62, "data": [f"score {HI} or more", f"score {MID} to {HI}"]},
        series=[bar(f"score {HI} or more", 0, "@good"),
                bar(f"score {MID} to {HI}", 1, "@warning/0.6")],
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
