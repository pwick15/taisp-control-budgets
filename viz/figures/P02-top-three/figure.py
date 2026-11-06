"""P02: the three leading monitor settings side by side, coloured against every setting we ran."""
import numpy as np

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P02",
    "title": "Haiku xhigh comes within {gap:.1f} points of Sonnet for far less",
    "section": "results",
    "order": 20,
    "caption": ("The three best monitor settings at a 2% audit budget. Colour ranks each value against all "
                "{n_runs} settings we ran: green is the best of them, red the worst. Cost is coloured on a log scale."),
    "notes": [],
}

TOP3 = [("Sonnet 5.5 · high", S.SONNET), ("Sonnet 5.5 · thinking off", S.SONNET_OFF), ("Haiku 5.5 · xhigh", S.HAIKU_X)]


def build() -> Figure:
    t = S.run_table()
    at2 = t[t.budget_pct == 2]
    caught = [S.row(t, run).safety_exact for _, run in TOP3]
    cost = [S.row(t, run).cost for _, run in TOP3]
    lo, hi = at2.safety_exact.min(), at2.safety_exact.max()
    logc = np.log(at2.cost.dropna().astype(float))
    cells = []
    for i, v in enumerate(caught):
        sub = "best of the three" if v == max(caught) else f"{100 * (max(caught) - v):.1f} points behind"
        cells.append({"col": 0, "row": i, "color": f"@goodbad:{(v - lo) / (hi - lo):.3f}",
                      "text": f"{{big|{100 * v:.1f}%}}\n{{small|{sub}}}"})
    for i, v in enumerate(cost):
        pos = 1 - (np.log(v) - logc.min()) / (logc.max() - logc.min())
        sub = "cheapest of the three" if v == min(cost) else f"{v / min(cost):.1f}x the cheapest"
        cells.append({"col": 1, "row": i, "color": f"@goodbad:{pos:.3f}", "text": f"{{big|${v:.4f}}}\n{{small|{sub}}}"})
    tab = C.heat_table(["Caught at a 2% budget", "Cost per program"], [n for n, _ in TOP3], cells, left=190, cell_h=74)
    data = [{"setting": n, "caught_2pct": c, "cost_per_program": k} for (n, _), c, k in zip(TOP3, caught, cost)]
    return Figure(option=tab["option"], height=tab["height"], data=data,
                  facts={"n_runs": t.run.nunique(), "gap": 100 * (caught[0] - caught[2])})
