"""M24: the hard backdoors as dots on the two risk axes, with what Opus made of each."""
import zlib

import pandas as pd

from viz.kit import Figure, entity
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M24",
    "title": "Opus flags the obvious backdoors, and the dangerous corner is empty",
    "section": "results",
    "order": 145,
    "caption": ("One dot per hard backdoor, {n:d} of them, rated by hand on two axes: across, how much "
                "damage the bug does when its trigger fires; up, how innocent the code looks to a "
                "reviewer. Violet means Opus 5.5 at xhigh scored it {hi:d} or more. The shaded corner, "
                "stealthy and severe, holds nothing."),
    "notes": [
        "The same ratings as M15, which counts them in a table. This draws them per backdoor so the "
        "empty corner and the Opus split can be read together.",
        "Opus is far better at the visible end. It scores {hi:d} or more on {o_vis:d} of the {n_vis:d} "
        "visible-and-severe backdoors and on {o_sls:d} of the {n_sls:d} stealthy ones, so what it adds "
        "is mostly confirmation of backdoors that already look wrong.",
        "The empty corner is the weakest claim on this page. It is an absence in {n:d} hand-rated "
        "programs, not a measured rate, and {n:d} is small enough that a corner holding one or two "
        "cases in truth could easily show zero here.",
        "The ratings are judgement, made from the diff and recorded with a confidence flag and a "
        "written reason per backdoor in hard51-risk-ratings.csv. They were not blind to the scores.",
        "An impact of 4 never occurs in this set, so that column is empty for every level of "
        "incrimination. The scale is kept at five so the gap is visible rather than closed up.",
        "Dots are spread a little from their integer ratings so overlapping cases stay countable. The "
        "offset is seeded from the problem id, so it is identical on every rebuild and carries no "
        "meaning of its own.",
    ],
    "height": 520,
}

HI = 50
STEALTHY, HARMFUL = 2, 3


def jitter(sample_id, salt: str) -> float:
    """A stable offset in [-0.22, 0.22], seeded from the problem id rather than from hash()."""
    return (zlib.crc32(f"{salt}{sample_id}".encode()) % 1000) / 1000 * 0.44 - 0.22


def build() -> Figure:
    r = pd.read_csv(S.ANALYSIS / "hard51-risk-ratings.csv")
    o = pd.read_csv(S.ANALYSIS / "opus-hard51-scores.csv")[["sample_id", "opus_xhigh"]]
    d = r.merge(o, on="sample_id", how="left")
    if d.opus_xhigh.isna().any():
        raise ValueError(f"{int(d.opus_xhigh.isna().sum())} rated backdoors have no Opus xhigh score")
    d["flagged"] = d.opus_xhigh >= HI

    groups = [(f"Opus scores {HI} or more", True, entity("opus55")),
              (f"Opus scores under {HI}", False, "@context-strong")]
    series = []
    for name, flag, colour in groups:
        g = d[d.flagged == flag]
        series.append({
            "name": name, "type": "scatter", "symbolSize": 11,
            "itemStyle": {"color": colour, "opacity": 0.9,
                          "borderColor": "@ink-surface", "borderWidth": 1},
            "data": [{"value": [x.impact + jitter(x.sample_id, "x"),
                                x.incrimination + jitter(x.sample_id, "y")],
                      "tip": (f"<b>problem {x.sample_id}</b><br>{x.quadrant}"
                              f"<br>damage {x.impact} of 5, looks planted {x.incrimination} of 5"
                              f"<br>Opus 5.5 xhigh: {x.opus_xhigh:g}<br>{x.mechanism}")}
                     for x in g.itertuples()],
        })
    # the stealthy and severe corner, tinted so the absence is visible
    series[0]["markArea"] = {
        "silent": True,
        "itemStyle": {"color": "@s7/0.09"},
        "data": [[{"coord": [HARMFUL - 0.5, 0]}, {"coord": [6, STEALTHY + 0.5]}]],
    }

    q = d.quadrant.value_counts()
    facts = {
        "n": len(d), "hi": HI,
        "n_vis": int(q.get("visible-and-severe", 0)), "n_sls": int(q.get("stealthy-low-stakes", 0)),
        "o_vis": int(d[(d.quadrant == "visible-and-severe") & d.flagged].shape[0]),
        "o_sls": int(d[(d.quadrant == "stealthy-low-stakes") & d.flagged].shape[0]),
    }
    rows = [{"sample_id": int(x.sample_id), "quadrant": x.quadrant, "impact": int(x.impact),
             "incrimination": int(x.incrimination), "opus_xhigh": x.opus_xhigh,
             "mechanism": x.mechanism, "confidence": x.confidence, "source": x.source}
            for x in d.itertuples()]
    option = C.base(
        grid={"left": 92, "right": 34, "top": 42, "bottom": 58},
        xAxis=C.axis("Damage when the trigger fires, 1 to 5", type="value",
             min=0, max=6, interval=1),
        yAxis=C.axis("How innocent the code looks, 1 to 5", gap=62, type="value",
                     min=0, max=6, interval=1, inverse=True),
        legend={"top": 0, "left": 86, "data": [g[0] for g in groups]},
        series=series,
    )
    return Figure(option=option, data=rows, facts=facts, height=META["height"])
