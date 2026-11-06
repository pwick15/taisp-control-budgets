"""P06: Sonnet 5.5 (high) against Haiku 5.5 (xhigh) at four audit budgets, as a coloured table."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P06",
    "title": "Sonnet's lead over Haiku xhigh grows as the budget tightens",
    "section": "results",
    "order": 60,
    "caption": ("Share of the 500 backdoors caught at four audit budgets, and Sonnet's lead in points. "
                "Colour ranks each catch rate against all {n_runs} monitor settings at that budget: green "
                "is the best of them, red the worst."),
    "notes": [
        "Every paired 95% interval for the lead excludes zero (they are in the CSV). The intervals widen as "
        "the budget tightens, so the size of the lead at 0.5% is uncertain even though its direction isn't.",
    ],
    "height": 320,
}

BUDGETS = (5, 2, 1, 0.5)
PAIR = [("Sonnet 5.5 · high", S.SONNET), ("Haiku 5.5 · xhigh", S.HAIKU_X)]


def build() -> Figure:
    t = S.run_table()
    diff = S.paired_diff(S.SONNET, S.HAIKU_X, BUDGETS)
    cells, rows = [], []
    for i, b in enumerate(BUDGETS):
        field = t[t.budget_pct == b].safety_exact
        vals = []
        for c, (_, run) in enumerate(PAIR):
            v = S.row(t, run, b).safety_exact
            pos = (v - field.min()) / (field.max() - field.min())
            cells.append({"col": c, "row": i, "color": f"@goodbad:{pos:.3f}", "text": f"{100 * v:.1f}%"})
            vals.append(v)
        d = diff[diff.budget_pct == b].iloc[0]
        cells.append({"col": 2, "row": i, "color": f"@seq:{min(1.0, d['diff'] / 0.3):.3f}", "text": f"+{100 * d['diff']:.1f}"})
        rows.append({"budget_pct": b, "sonnet": vals[0], "haiku_xhigh": vals[1],
                     "lead": d["diff"], "lead_lo": d["lo"], "lead_hi": d["hi"]})
    tab = C.heat_table([p[0] for p in PAIR] + ["Sonnet's lead (points)"],
                       [f"{b:g}% budget" for b in BUDGETS], cells, left=112)
    return Figure(option=tab["option"], height=tab["height"], data=rows, facts={"n_runs": t.run.nunique()})
