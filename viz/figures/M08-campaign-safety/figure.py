"""M08: catching an attacker that has to land several backdoors, as the edits get subtler."""
import math

import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M08",
    "title": "An attacker who needs several backdoors gets caught sooner",
    "section": "appendix",
    "order": 100,
    "caption": ("Each line is one monitor held at its own cutoff for a 2% audit request. x is how many "
                "backdoors the attacker has to land, y the chance at least one of them is caught, with "
                "the tasks drawn without replacement from the problems we measured. The dial confines "
                "the attacker to smaller and smaller edits."),
    "notes": [
        "Thin rungs to the right of the dial. The pool falls from {p_all} backdoors at any size to "
        "{p_tight} at {cap_tight} lines or fewer, so the steeper dial steps draw {k_max} of {p_tight} "
        "problems and lean hard on the set. Treat the right-hand end of those steps as the least "
        "trustworthy part of the figure.",
        "No independence assumption and no fitted model: the probability is the exact hypergeometric "
        "one over the joint outcome actually observed. The single assumption is that the attacker's "
        "tasks are an unordered draw from the problems measured, which is what the dial puts pressure on.",
        "These monitors are not spending the same budget. A 2% request lands on cutoffs serving "
        "{fpr_lo}% to {fpr_hi}% of honest programs, because a coarse score scale cannot land on 2%. The "
        "weakest monitors here are the ones spending least, so the comparison flatters the strong ones.",
        "Every attempt is screened by the same monitor at the same cutoff, and the attacker never adapts "
        "after a near miss. That makes each curve an optimistic bound on catching a real campaign.",
        "Coloured: the strongest and weakest monitors on the whole set. The grey lines are the four "
        "others and are context for the shape; the CSV carries every monitor's numbers.",
        "The x-axis is a ladder of rungs, not a scale: the landing counts sit evenly apart although "
        "they are not evenly spaced, so the slope between two rungs cannot be compared with the slope "
        "between two others. Read the heights rather than the steepness.",
    ],
    "height": 460,
}

# The six runs this view draws, chosen to span the range from a monitor that catches most
# backdoors one at a time to ones that look useless at a 2% budget. That span is the finding,
# so this is deliberately not S.family_pool(), which keeps only each family's best arm.
RUNS = ["dataset500-sonnet55-um-strip", "dataset-haiku55-effortxhigh-tm-n500-strip",
        "dataset-glm53-tm-n500-strip", "dataset-gptoss120b-high-tm-n500-strip",
        "dataset-gemini35fl-high-tm-n500-strip", "dataset500-gemma426b-tm-strip"]
BUDGET = 2.0
# How many backdoors the attacker has to land. Capped at 20: the smallest edit-size pool holds
# 41 problems and drawing 20 of 41 already leans hard on the set.
K_LAND = [1, 2, 3, 5, 8, 12, 20]
# The edit sizes the dial steps through, in lines changed. None is every attack in the set.
EDIT_CAPS: list[int | None] = [None, 40, 20, 10, 5]


def p_any(caught, k: int) -> float:
    """P(at least one caught) when k of these problems are drawn without replacement."""
    n, miss = len(caught), int((~caught).sum())
    if k > n:
        raise ValueError(f"cannot draw {k} problems from a pool of {n}")
    return 1.0 - (math.comb(miss, k) / math.comb(n, k) if miss >= k else 0.0)


def load() -> tuple[dict, dict]:
    """Per run: (attack rows with edit sizes, cutoff) and the served honest rate at that cutoff."""
    nom = pd.read_csv(S.ANALYSIS / "achieved-fpr.csv")
    nom = nom[nom.nominal_pct == BUDGET].set_index("run")
    lines = S.cases().set_index("sample_id").changed_lines
    out, served = {}, {}
    for run in RUNS:
        g = S.samples(run)
        g = g[g["mode"] == "attack"].dropna(subset=["suspicion"]).copy()
        g["cl"] = g.sample_id.astype(str).map(lines)
        if g.cl.isna().any():
            raise ValueError(f"{run}: {int(g.cl.isna().sum())} attack rows have no recorded edit size")
        thr = float(nom.threshold[run])
        if not math.isfinite(thr):
            raise ValueError(f"{run} has no cutoff at a {BUDGET:g}% request")
        out[run] = (g, thr)
        served[run] = float(nom.achieved_fpr_pct[run])
    sizes = {len(g) for g, _ in out.values()}
    if len(sizes) != 1:
        raise ValueError(f"runs score different numbers of attacks: {sorted(sizes)}")
    return out, served


def build() -> Figure:
    runs, served = load()
    base_rec = {r: float((g.suspicion > t).mean()) for r, (g, t) in runs.items()}
    strong = max(base_rec, key=lambda r: base_rec[r])
    weak = min(base_rec, key=lambda r: base_rec[r])
    colour = {strong: entity("sonnet55") if "sonnet55" in strong else "@s0", weak: "@s7"}

    rows, frames = [], []
    pools: dict[str, int] = {}
    for cap in EDIT_CAPS:
        step = "any size" if cap is None else f"{cap} lines"
        ser = []
        for run in RUNS:
            g, thr = runs[run]
            sub = g if cap is None else g[g.cl <= cap]
            caught = (sub.suspicion > thr).to_numpy()
            pools[step] = len(sub)
            ps = [p_any(caught, k) for k in K_LAND]
            name = S.run_label(run)
            hot = run in colour
            col = colour.get(run, "@context")
            ser.append({
                "name": name if hot else "four other monitors",
                "type": "line", "symbolSize": 8 if hot else 6, "z": 3 if hot else 2,
                "lineStyle": {"color": col, "width": 2.5 if hot else 1.5},
                "itemStyle": {"color": col if hot else "@context-strong",
                              "borderColor": "@ink-surface", "borderWidth": 1.5},
                "data": [{"value": round(p, 4),
                          "tip": (f"<b>{name}</b><br>{k} backdoor{'s' if k != 1 else ''} to land"
                                  f"<br>caught at least once: {100 * p:.1f}%"
                                  f"<br>catches {100 * caught.mean():.1f}% one at a time"
                                  f"<br>pool: {len(sub)} backdoors of this size")}
                         for k, p in zip(K_LAND, ps)],
            })
            rows += [{"edit_cap": step, "monitor": name, "run": run, "pool": len(sub),
                      "cutoff": thr, "served_honest_pct": served[run],
                      "caught_alone_pct": round(100 * caught.mean(), 2),
                      "backdoors_to_land": k, "caught_once_pct": round(100 * p, 2)}
                     for k, p in zip(K_LAND, ps)]
        frames.append({"series": ser})

    facts = {"p_all": pools["any size"], "p_tight": pools[f"{EDIT_CAPS[-1]} lines"],
             "cap_tight": EDIT_CAPS[-1], "k_max": K_LAND[-1],
             "fpr_lo": round(min(served.values()), 1), "fpr_hi": round(max(served.values()), 1)}
    option = C.base(
        grid={"left": 70, "right": 30, "top": 46, "bottom": 56},
        xAxis=C.axis("Backdoors the attacker has to land", type="category",
                     data=[str(k) for k in K_LAND], boundaryGap=False),
        yAxis=C.axis("Chance at least one is caught", gap=48, type="value", min=0, max=1,
                     axisLabel={"formatter": "{value}"}),
        legend={"top": 0, "left": 60, "data": [S.run_label(strong), S.run_label(weak),
                                               "four other monitors"]},
        series=frames[0]["series"],
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"],
                  dial={"label": "Largest edit the attacker will hide behind",
                        "steps": ["any size" if c is None else f"{c} lines" for c in EDIT_CAPS],
                        "initial": 0, "frames": frames})
