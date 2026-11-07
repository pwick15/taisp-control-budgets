"""P10: backdoors grouped by how many lines they change, split by how many monitors caught them."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P10",
    "title": "Small edits get past monitors far more often",
    "section": "results",
    "order": 100,
    "caption": ("All 500 backdoors, grouped by how many lines differ from the honest reference solution and split "
                "like P11 by how many of seven monitors caught them at a 2% budget. On the right is the 95% range "
                "for the share missed by all seven."),
    "notes": [
        "Lines changed is measured against the dataset's reference solution, not against what an honest model "
        "would write, so a big number can mean a rewrite rather than a big backdoor.",
        "Size and writer are tangled: o3-mini's backdoors change the most lines and are the easiest to catch "
        "(P11). This figure alone can't say which one drives the other.",
    ],
}

BINS = [(0, 4, "1 to 4 lines"), (5, 8, "5 to 8 lines"), (9, 20, "9 to 20 lines"), (21, 10 ** 9, "21 or more lines")]
PARTS = [("Missed by all 7", "@s7", "@on-strong"), ("Missed by some", "@warning/0.6", "@on-bright"),
         ("Caught by all 7", "@context", "@on-pale")]


def build() -> Figure:
    cf = S.cases()
    rows, data = [], []
    for lo, hi, label in BINS:
        g = cf[(cf.changed_lines >= lo) & (cf.changed_lines <= hi)]
        c = [int((g.caught_by == 0).sum()), int(((g.caught_by > 0) & (g.caught_by < 7)).sum()), int((g.caught_by == 7).sum())]
        rows.append((label, len(g), c))
        data.append({"lines": label, "n": len(g), "missed_all": c[0], "missed_some": c[1], "caught_all": c[2]})
    option = C.partition_bars(rows, PARTS, "Share of backdoors in that size group", "Missed by all, 95% range")
    return Figure(option=option, height=110 + 40 * len(rows), data=data)
