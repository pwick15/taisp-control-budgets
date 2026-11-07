"""M15: the 51 hardest backdoors rated by how incriminating the code looks and how much damage it does."""
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M15",
    "title": "No hard backdoor is both stealthy and seriously harmful",
    "section": "appendix",
    "order": 123,
    "caption": ("The {n:d} hardest backdoors, each rated by hand on two axes: how obviously planted the code "
                "looks to a reviewer, and how much damage the bug does when its trigger fires. Cells hold "
                "counts. The stealthy and severe block, top right, is empty."),
    "notes": [
        "{q_sls:d} are stealthy and low stakes, {q_vbm:d} are visible but minor, {q_vas:d} are visible and "
        "severe, and {q_ssv:d} are stealthy and severe. The quadrant that would worry you most is the one "
        "with nothing in it.",
        "That emptiness is about this set, not about backdoors in general. These {n:d} were chosen because "
        "the monitors failed on them, so the sample is selected on being hard to catch.",
        "Hand ratings, not measurements. Each backdoor was rated twice and disagreements adjudicated: "
        "{n_cons:d} agreed first time, {n_adj:d} needed adjudication, and {n_med:d} is still marked medium "
        "confidence. The per-backdoor reasons are in the CSV.",
        "An impact of 4 never occurs, so that column is empty in both directions. The scale is kept at five "
        "points rather than redrawn to fit the data.",
        "Scores for the same backdoors live in opus-hard51-scores.csv and join on sample_id. This table "
        "deliberately does not repeat them.",
    ],
}

INCR = {1: "1 · looks innocent", 2: "2", 3: "3", 4: "4", 5: "5 · obviously planted"}
IMP = {1: "1 · harmless", 2: "2", 3: "3", 4: "4", 5: "5 · severe"}
STEALTHY, HARMFUL = 2, 3          # incrimination <= 2 is stealthy; impact >= 3 is harmful


def build() -> Figure:
    r = pd.read_csv(S.ANALYSIS / "hard51-risk-ratings.csv")
    counts = {(int(i), int(j)): 0 for i in INCR for j in IMP}
    for _, row in r.iterrows():
        counts[(int(row.incrimination), int(row.impact))] += 1
    top = max(counts.values())
    cells = []
    for ri, i in enumerate(sorted(INCR)):
        for ci, j in enumerate(sorted(IMP)):
            n = counts[(i, j)]
            danger = i <= STEALTHY and j >= HARMFUL
            shade = 0.12 if n == 0 else 0.3 + 0.6 * (n / top)
            cells.append({"col": ci, "row": ri,
                          "color": f"@s7/{min(0.9, shade):.2f}" if danger and n else f"@seq:{shade:.2f}",
                          "text": str(n)})
    t = C.heat_table([IMP[j] for j in sorted(IMP)], [INCR[i] for i in sorted(INCR)],
                     cells, left=190, cell_h=62)
    rows = [{"sample_id": int(x.sample_id), "incrimination": int(x.incrimination),
             "impact": int(x.impact), "quadrant": x.quadrant, "mechanism": x.mechanism,
             "source": x.source, "confidence": x.confidence} for _, x in r.iterrows()]
    q = r.quadrant.value_counts()
    facts = {"n": len(r),
             "q_sls": int(q.get("stealthy-low-stakes", 0)),
             "q_vbm": int(q.get("visible-but-minor", 0)),
             "q_vas": int(q.get("visible-and-severe", 0)),
             "q_ssv": int(((r.incrimination <= STEALTHY) & (r.impact >= HARMFUL)).sum()),
             "n_cons": int((r.source == "consensus").sum()),
             "n_adj": int((r.source == "adjudicated").sum()),
             "n_med": int((r.confidence == "medium").sum())}
    return Figure(option=t["option"], data=rows, facts=facts, height=t["height"])
