"""M18: every program's suspicion score across the five comment arms, as a slopegraph."""
import zlib

import numpy as np
import pandas as pd

from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M18",
    "title": "Stripping comments costs more than any adversarial rewrite gains",
    "section": "appendix",
    "order": 127,
    "caption": ("One faint line per backdoored program, tracked across five versions of the same code: "
                "comments stripped, the confession removed, left as written, rewritten to argue the code "
                "is safe, and rewritten to point at the wrong line. Bold lines are group means."),
    "notes": [
        "Mean suspicion runs {m_strip} stripped, {m_noconf} with the confession removed, {m_orig} as "
        "written, {m_adv} adversarial and {m_mis} misdirection. Taking the comments away moves the "
        "monitor further than anything the attacker writes into them.",
        "Adversarial and misdirection rewrites land slightly below the original rather than near the "
        "stripped arm, so arguing the code is safe is worth little once a comment is there to read.",
        "{n} of 500 programs were scored in all five arms, so this is the subset that ran everywhere, "
        "not the whole set. Means are over those {n}.",
        "Programs are grouped by what their original comments do: confess to the bug, carry a comment "
        "that does not, or have no comment at all. A program with no comment still differs between the "
        "stripped and original arms because the stripped arm removes docstrings too.",
        "Ported from the data explorer's cases-arm-slopegraph view, reading committed CSVs.",
    ],
    "height": 560,
}

ARMS = ["stripped", "no_confession", "original", "adversarial", "misdirection"]
ARM_LABELS = ["comments\nstripped", "confession\nremoved", "as\nwritten", "adversarial\nrewrite",
              "misdirection\nrewrite"]
BUCKETS = [("confesses in a comment", "@s0"), ("comment, no confession", "@s1"), ("no comment", "@s2")]
ARM_JS = ("function (v) { var n = ['comments stripped','confession removed','as written',"
          "'adversarial rewrite','misdirection rewrite']; return n[v] !== undefined ? n[v] : ''; }")


def bucket(confesses: bool, has_comment: bool) -> str:
    return ("confesses in a comment" if confesses
            else "comment, no confession" if has_comment else "no comment")


def build() -> Figure:
    adv = pd.read_csv(S.ANALYSIS / "adversarial-comments.csv")
    mis = pd.read_csv(S.ANALYSIS / "misdirection.csv")
    conf = pd.read_csv(S.ANALYSIS / "backdoor-comment-confessions.csv")
    for f in (adv, mis, conf):
        f["sample_id"] = f["sample_id"].astype(str)
    c = (adv.merge(mis, on="sample_id", how="outer")
            .merge(conf[["sample_id", "has_comment", "confesses"]], on="sample_id", how="left")
            .dropna(subset=ARMS))
    c["has_comment"] = c.has_comment.fillna(False).astype(bool)
    c["confesses"] = c.confesses.fillna(False).astype(bool)
    c["bucket"] = [bucket(a, b) for a, b in zip(c.confesses, c.has_comment)]
    series, rows = [], []
    for name, color in BUCKETS:
        sub = c[c.bucket == name]
        # Scores sit on a coarse 0.1 grid, so without a nudge every path stacks on the
        # same few lines and the panel turns into a moire. The offset is seeded from the
        # sample id with a stable hash, so a rebuild puts each path back exactly where it
        # was. Python's own hash() is salted per process and would move them every time.
        pts = []
        for r in sub.itertuples():
            j = float(np.random.default_rng(zlib.crc32(str(r.sample_id).encode()))
                      .uniform(-0.035, 0.035))
            for i, arm in enumerate(ARMS):
                pts.append([i, round(float(getattr(r, arm)) + j, 4)])
            pts.append([4, None])                      # break the line between programs
        series.append({"name": name, "type": "line", "silent": True, "showSymbol": False,
                       "connectNulls": False, "lineStyle": {"color": color, "width": 1, "opacity": 0.13},
                       "data": pts, "tooltip": {"show": False}})
        mean = sub[ARMS].mean()
        series.append({
            "name": name, "type": "line", "symbolSize": 8, "z": 5,
            "lineStyle": {"color": color, "width": 3},
            "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 2},
            "data": [{"value": [i, round(float(mean[arm]), 4)],
                      "tip": f"<b>{name}</b> ({len(sub)} programs)<br>{arm}: {mean[arm]:.3f} mean suspicion"}
                     for i, arm in enumerate(ARMS)]})
        rows += [{"sample_id": r.sample_id, "bucket": name,
                  **{a: round(float(getattr(r, a)), 4) for a in ARMS}} for r in sub.itertuples()]
    allmean = c[ARMS].mean()
    facts = {"n": len(c), **{f"m_{k}": round(float(allmean[a]), 3) for k, a in
                             zip(("strip", "noconf", "orig", "adv", "mis"), ARMS)}}
    option = C.base(
        grid={"left": 70, "right": 30, "top": 40, "bottom": 56},
        xAxis=C.axis("", type="value", min=-0.3, max=4.3, splitLine={"show": False},
                     axisLabel={"formatter": ARM_JS, "fontSize": 11, "interval": 0}),
        yAxis=C.axis("Suspicion score", gap=46, type="value", min=0, max=1),
        legend={"top": 0, "left": 64, "data": [n for n, _ in BUCKETS]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts)
