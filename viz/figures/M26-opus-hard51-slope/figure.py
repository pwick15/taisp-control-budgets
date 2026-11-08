"""M26: variation on M22. Each hard backdoor as a line across the three monitors that read it."""
import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M26",
    "title": "Most hard backdoors stay flat across all three monitors",
    "section": "results",
    "order": 137,
    "caption": ("A variation on M22. One line per hard backdoor, {n:d} of them, tracking the same "
                "code across the three monitors that read it. A line that climbs on the right is a "
                "backdoor Opus found suspicious and the small monitors did not. {n_flat:d} of the "
                "lines never leave the bottom band."),
    "notes": [
        "Same data as M22, read along rather than down. This form answers whether a backdoor's score "
        "is a property of the program or of the monitor: a bundle of parallel lines would mean the "
        "program, and a fan means the monitor.",
        "Violet lines are backdoors no monitor caught. Grey lines are the ones a panel monitor did "
        "catch, which is why they are in this hard set but not in the never-caught group of {n_nc:d}.",
        "The three columns are not a scale or a sequence. They are three monitors in a fixed order, "
        "so the horizontal distance between them means nothing and only the vertical moves do.",
        "Sonnet and Haiku are nearly flat against each other, medians {son_med:g} and {hai_med:g} out "
        "of 100, which is what makes this set hard. Almost all of the movement is in the last step.",
        "Lines overlap heavily at the bottom, so the band below {flat:d} is a thicket rather than "
        "{n_flat:d} readable lines. Use M22 to read an individual backdoor.",
    ],
    "height": 560,
}

COLS = [("Haiku 5.5 xhigh", "haiku"), ("Sonnet 5.5", "sonnet"), ("Opus 5.5 xhigh", "opus_xhigh")]
FLAT = 20
GROUPS = [("No monitor caught it", "never_caught", f"{entity('opus55')}/0.75", 3),
          ("A panel monitor caught it", None, "@context-strong/0.6", 2)]


def build() -> Figure:
    d = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")
    d = d.rename(columns={"Haiku 5.5 xhigh": "haiku", "Sonnet 5.5": "sonnet"})
    d["sample_id"] = d.sample_id.astype(str)

    series, rows = [], []
    for name, grp, colour, z in GROUPS:
        g = d[d.group == grp] if grp else d[d.group != "never_caught"]
        for r in g.itertuples():
            vals = [getattr(r, c) for _, c in COLS]
            series.append({
                "name": name, "type": "line", "symbolSize": 6, "z": z,
                "lineStyle": {"color": colour, "width": 1.5},
                "itemStyle": {"color": colour},
                "data": [{"value": v,
                          "tip": (f"<b>problem {r.sample_id}</b><br>{lab}: {v:g} of 100"
                                  f"<br>{'caught by no monitor' if grp else 'caught by a panel monitor'}")}
                         for (lab, _), v in zip(COLS, vals)],
            })
        rows += [{"sample_id": r.sample_id, "group": r.group,
                  **{c: getattr(r, c) for _, c in COLS}} for r in g.itertuples()]

    flat = d[[c for _, c in COLS]].max(axis=1) < FLAT
    facts = {"n": len(d), "n_flat": int(flat.sum()), "flat": FLAT,
             "n_nc": int((d.group == "never_caught").sum()),
             "son_med": float(d.sonnet.median()), "hai_med": float(d.haiku.median())}
    option = C.base(
        grid={"left": 66, "right": 48, "top": 40, "bottom": 56},
        xAxis=C.axis("", type="category", data=[c for c, _ in COLS], boundaryGap=False),
        yAxis=C.axis("Suspicion score, 0 to 100", gap=46, type="value", min=0, max=100, interval=20),
        legend={"top": 0, "left": 60, "itemGap": 18, "data": [g[0] for g in GROUPS]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
