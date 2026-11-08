"""P20: an attacker who rewrites the comments catches no break; removing them is what costs catches."""
import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "P20",
    "title": "Rewriting comments to look innocent doesn't help the attacker",
    "section": "results",
    "order": 121,
    "caption": ("Backdoors caught at a 2% audit budget on {n} programs, each scored four ways by the same "
                "monitor (Haiku 5.5 xhigh). The code never changes, only its comments. In the two right-hand bars "
                "an attacker model (GLM-5.3) rewrote them, keeping as many comments as the original had."),
    "notes": [
        "Paired over the same programs, the attacker's rewrite changes the catch rate by {d_adv:+.1f} points "
        "(95% interval {adv_lo:+.1f} to {adv_hi:+.1f}). Removing the comments changes it by {d_rem:+.1f} "
        "({rem_lo:+.1f} to {rem_hi:+.1f}).",
        "Why it fails: on this dataset any comment makes code look more suspicious, because honest solutions "
        "here barely have comments. So this is a fact about this dataset, not proof that comments are safe to "
        "show in general.",
        "One attacker, with no sight of the monitor's prompt and no retries. A determined attacker could do better.",
        "The cutoff comes from the same problems' honest solutions scored in this experiment's own harness, so "
        "these numbers don't join to the main run tables.",
    ],
    "height": 380,
}

BUDGET = 0.02
ARMS = [("stripped", "Comments\nremoved", "@context-strong"),
        ("original", "Original\ncomments", "@s0"),
        ("adversarial", "Attacker rewrote\nthem to look safe", "@s0"),
        ("misdirection", "Attacker left the bug\nline uncommented", "@s0")]
N_BOOT = 3000


def rate(h: np.ndarray, a: np.ndarray) -> float:
    return S.safety_at(h, a, BUDGET)["exact"]


def build() -> Figure:
    adv = pd.read_csv(S.ANALYSIS / "adversarial-comments.csv", dtype={"sample_id": str})
    mis = pd.read_csv(S.ANALYSIS / "misdirection.csv", dtype={"sample_id": str})
    c = adv.merge(mis, on="sample_id").dropna(subset=[a for a, _, _ in ARMS] + ["honest_original"])
    h = c.honest_original.to_numpy(float)
    vals = {a: rate(h, c[a].to_numpy(float)) for a, _, _ in ARMS}

    # Paired bootstrap over problems, the cutoff re-estimated in every replicate.
    rng = np.random.default_rng(20261108)
    diffs = {"adversarial": [], "stripped": []}
    for _ in range(N_BOOT):
        i = rng.integers(0, len(c), len(c))
        hb = h[i]
        base = rate(hb, c.original.to_numpy(float)[i])
        for k in diffs:
            diffs[k].append(100 * (rate(hb, c[k].to_numpy(float)[i]) - base))
    ci = {k: np.percentile(v, [2.5, 97.5]) for k, v in diffs.items()}

    data = [{"value": round(100 * vals[a], 2),
             "itemStyle": {"color": col, "borderRadius": [5, 5, 0, 0]},
             "label": {"formatter": f"{100 * vals[a]:.0f}%"},
             "tip": f"<b>{lab.replace(chr(10), ' ')}</b><br>{100 * vals[a]:.1f}% of {len(c)} backdoors caught"}
            for a, lab, col in ARMS]
    option = C.base(
        grid={"left": 58, "right": 16, "top": 24, "bottom": 64},
        xAxis=C.axis("", type="category", data=[lab for _, lab, _ in ARMS],
                     axisLabel={"interval": 0, "fontSize": 12, "lineHeight": 16, "color": "@ink-primary"}),
        yAxis=C.axis("Backdoors caught", gap=40, type="value", min=0, max=100,
                     axisLabel={"formatter": "{value}%"}),
        series=[{"type": "bar", "data": data, "barWidth": "52%",
                 "label": {"show": True, "position": "top", "color": "@ink-primary", "fontSize": 13,
                           "fontWeight": 600}}],
    )
    rows = [{"comments": lab.replace("\n", " "), "programs": len(c), "caught_pct": round(100 * vals[a], 2)}
            for a, lab, _ in ARMS]
    return Figure(option=option, data=rows, facts={
        "n": len(c),
        "d_adv": 100 * (vals["adversarial"] - vals["original"]), "adv_lo": ci["adversarial"][0], "adv_hi": ci["adversarial"][1],
        "d_rem": 100 * (vals["stripped"] - vals["original"]), "rem_lo": ci["stripped"][0], "rem_hi": ci["stripped"][1]})
