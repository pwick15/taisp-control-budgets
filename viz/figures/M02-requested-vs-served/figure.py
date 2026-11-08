"""M02: where each requested audit budget actually lands once a monitor has to serve it."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M02",
    "title": "Few budget requests audit exactly the share asked for",
    "section": "appendix",
    "order": 135,
    "caption": ("Every cell of the study's budget table: a requested budget on the left, where that "
                "monitor's threshold actually landed on the right. A band is drawn only when the served "
                "rate misses the request. Thickness is the number of cells."),
    "notes": [
        "{n_exact} of {n} cells serve the rate they were asked for. The rest snap to whatever cutoff the "
        "monitor's own honest scores allow, which is almost always cheaper than the request.",
        "{n_zero} cells serve nothing at all: no honest score sits above the cutoff, so the budget cannot "
        "be spent and the monitor catches nothing at that setting.",
        "Not one of the {n_runs} runs can serve a {tight}% request exactly. That column is arithmetic, "
        "not monitor quality: {tight}% of 500 honest programs is under three rows.",
        "Data quality: this counts cells, so a monitor with many runs weighs more than one with few. It "
        "says how often a requested budget is honoured across the table, not how often a given monitor "
        "honours one.",
        "Ported from the data explorer's b1-requested-vs-served view, reading achieved-fpr.csv.",
    ],
    "height": 620,
}

BANDS = [(0.5, "over 0% up to 0.5%"), (1, "over 0.5% up to 1%"), (2, "over 1% up to 2%"),
         (5, "over 2% up to 5%"), (10, "over 5% up to 10%"), (20, "over 10% up to 20%"),
         (50, "over 20% up to 50%")]
EXACT, ZERO = "exactly as asked", "served nothing"


def band(v: float) -> str:
    return next((lab for hi, lab in BANDS if v <= hi), "over 50%")


def build() -> Figure:
    af = pd.read_csv(S.ANALYSIS / "achieved-fpr.csv")
    c = af[(af.n_honest == 500) & (af.n_attack == 500)]
    flow: dict[tuple[str, str, str], int] = {}
    for r in c.itertuples():
        src = f"asked for {r.nominal_pct:g}%"
        if r.achieved_fpr_pct <= 1e-9:
            tgt, kind = ZERO, "zero"
        elif r.exact:
            tgt, kind = EXACT, "exact"
        else:
            tgt, kind = band(r.achieved_fpr_pct), "snapped"
        flow[(src, tgt, kind)] = flow.get((src, tgt, kind), 0) + 1
    right = [EXACT] + [lab for _, lab in BANDS][::-1] + [ZERO]
    used = {t for _, t, _ in flow}
    colour = {"exact": "@good", "snapped": "@context-strong", "zero": "@s7"}
    nodes = [{"name": f"asked for {v:g}%", "itemStyle": {"color": "@ink-muted"}}
             for v in sorted(c.nominal_pct.unique())]
    nodes += [{"name": n, "itemStyle": {"color": "@good" if n == EXACT
                                        else "@s7" if n == ZERO else "@context-strong"}}
              for n in right if n in used]
    links = [{"source": s, "target": t, "value": n,
              "lineStyle": {"color": colour[k], "opacity": 0.45}}
             for (s, t, k), n in sorted(flow.items())]
    option = C.base(
        series=[{"type": "sankey", "left": 18, "right": 215, "top": 16, "bottom": 16,
                 "nodeWidth": 14, "nodeGap": 10, "layoutIterations": 0, "draggable": False,
                 "emphasis": {"focus": "adjacency"},
                 "label": {"color": "@ink-primary", "fontSize": 11},
                 "lineStyle": {"curveness": 0.45}, "data": nodes, "links": links}],
    )
    option.pop("grid", None)
    option.pop("xAxis", None)
    option.pop("yAxis", None)
    rows = [{"asked_pct": s.replace("asked for ", "").rstrip("%"), "served": t, "kind": k, "cells": n}
            for (s, t, k), n in sorted(flow.items())]
    tight = float(c.nominal_pct.min())
    facts = {"n": len(c), "n_runs": c.run.nunique(),
             "n_exact": int(c.exact.sum()), "n_zero": int((c.achieved_fpr_pct <= 1e-9).sum()),
             "tight": f"{tight:g}"}
    return Figure(option=option, data=rows, facts=facts)
