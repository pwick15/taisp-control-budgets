"""M19: how big the diff is for backdoors no monitor caught, against the ones at least one caught."""
import numpy as np

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M19",
    "title": "The backdoors nothing caught are the small edits",
    "section": "appendix",
    "order": 133,
    "caption": ("Both groups of the 500 backdoored programs, as cumulative curves: the share of each "
                "group whose diff changes at most the number of lines across. A curve further left is a "
                "group of smaller edits. Dashed lines mark the two medians."),
    "notes": [
        "The {n_surv} programs no monitor caught change a median of {med_surv} lines against {med_rest} "
        "for the {n_rest} that at least one caught. As a share of the program it is {rat_surv} against "
        "{rat_rest}, so the survivors edit about half the file and the rest rewrite more than all of it.",
        "Data quality: the split is defined at a {pct}% audit budget across seven monitors. Move the "
        "budget and the groups change, so this is a statement about that operating point rather than "
        "about backdoors in general.",
        "Only {n_surv} programs survive, so the left curve is built from few points and steps coarsely. "
        "Read the separation between the curves, not the shape of either one.",
        "Edit size and generator are confounded here. o3-mini wrote {o3_rest}% of the caught group but "
        "only {o3_surv}% of the survivors, and it also writes the largest diffs, so some of this gap is "
        "which model was asked rather than how big the edit is.",
        "Ported from the data explorer's cases-never-caught-structure view.",
    ],
    "height": 520,
}

GROUPS = [("No monitor caught it", "@s7"), ("At least one caught it", "@context-strong")]
BUDGET = 2


def ecdf(v: np.ndarray) -> list[list[float]]:
    x = np.sort(v[v > 0])
    return [[float(xi), round(float((i + 1) / len(x)), 4)] for i, xi in enumerate(x)]


def build() -> Figure:
    c = S.cases().copy()
    c["ratio"] = c.changed_lines / c.code_lines
    surv, rest = c[c.caught_by == 0], c[c.caught_by > 0]
    series, rows = [], []
    for (name, color), g in zip(GROUPS, (surv, rest)):
        pts = ecdf(g.changed_lines.to_numpy(float))
        series.append({
            "name": f"{name} ({len(g)})", "type": "line", "step": "end", "showSymbol": False,
            "lineStyle": {"color": color, "width": 2.5}, "itemStyle": {"color": color},
            "data": [{"value": p, "tip": f"<b>{name}</b><br>{p[0]:.0f} lines or fewer<br>"
                                        f"{100 * p[1]:.0f}% of the group"} for p in pts],
            "markLine": {"silent": True, "symbol": "none",
                         "lineStyle": {"color": color, "type": "dashed", "width": 1.5},
                         "label": {"show": False},
                         "data": [{"xAxis": float(g.changed_lines.median())}]},
        })
        rows += [{"group": name, "sample_id": r.sample_id, "changed_lines": int(r.changed_lines),
                  "code_lines": int(r.code_lines), "ratio": round(float(r.ratio), 4)}
                 for r in g.itertuples()]
    mix = c.groupby("model").apply(
        lambda g: (len(g[g.caught_by == 0]), len(g[g.caught_by > 0])), include_groups=False)
    o3 = mix.get("openai/o3-mini", (0, 0))
    facts = {"n_surv": len(surv), "n_rest": len(rest), "pct": BUDGET,
             "med_surv": int(surv.changed_lines.median()), "med_rest": int(rest.changed_lines.median()),
             "rat_surv": round(float(surv.ratio.median()), 2), "rat_rest": round(float(rest.ratio.median()), 2),
             "o3_surv": round(100 * o3[0] / max(len(surv), 1)), "o3_rest": round(100 * o3[1] / max(len(rest), 1))}
    option = C.base(
        grid={"left": 76, "right": 34, "top": 40, "bottom": 58},
        xAxis=C.axis("Lines the diff changes (log scale)", type="log", min=1, max=400),
        yAxis=C.axis("Share of the group at or below", gap=52, type="value", min=0, max=1,
                     axisLabel={"formatter": "function (v) { return (v * 100) + '%'; }"}),
        legend={"top": 0, "left": 70, "data": [f"{n} ({len(g)})" for (n, _), g in zip(GROUPS, (surv, rest))]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts)
