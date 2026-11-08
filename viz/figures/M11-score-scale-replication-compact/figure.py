"""M11: both batches and both score scales for one monitor in a single panel, monitor on the dial."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M11",
    "title": "Both batches agree: the 0 to 100 scale offers more cutoffs",
    "section": "appendix",
    "order": 112,
    "caption": ("One monitor at a time, with both problem batches overlaid. Each distinct honest score is one "
                "cutoff: x is the share of honest programs audited, y the backdoors caught. Filled marks are "
                "the original 500, hollow marks the second 500. The dashed line is a 5% audit share."),
    "notes": [
        "The compact cut of M09 and M10, for when the point is that the two batches tell the same story "
        "rather than how each one looks.",
        "Orange sits left of and above blue in both batches, which is the whole claim: a wider score scale "
        "puts more operating points within reach, including cheaper ones.",
        "Hollow marks the second batch rather than a dashed line, because a dashed line in this project "
        "means a threshold and nothing else.",
        "Sonnet's 0 to 10 arm on batch 2 appears as a single hollow blue mark. That is not a drawing "
        "error: the arm produced {son_b2_distinct:d} distinct honest scores and so one usable cutoff.",
    ],
    "height": 470,
}

SCALES = [("0-10", "@s0"), ("0-100", "@s1")]
XA = {"type": "log", "min": 0.2, "max": 60, "axisLabel": {"formatter": "{value}%"}}
FIVE = {"silent": True, "symbol": "none", "label": {"show": False},
        "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1},
        "data": [{"xAxis": 5}]}
NAMES = {("0-10", 0): "0-10 · original", ("0-100", 0): "0-100 · original",
         ("0-10", 1): "0-10 · batch 2", ("0-100", 1): "0-100 · batch 2"}


def series_for(monitor: str, rows: list) -> list:
    out, first = [], True
    for bi, batch in enumerate(S.SCALE_BATCHES):
        hollow = bi == 1
        for scale, color in SCALES:
            run = S.SCALE_RUNS[(monitor, batch)][scale]
            r = S.resolution_curve(run)
            out.append({
                "name": NAMES[(scale, bi)], "type": "line", "step": "end", "symbolSize": 9,
                "itemStyle": {"color": "@ink-surface" if hollow else color,
                              "borderColor": color, "borderWidth": 2 if hollow else 1.5},
                "lineStyle": {"color": color, "width": 1.5 if hollow else 2.5,
                              **({"opacity": 0.75} if hollow else {})},
                "data": [{"value": [round(f, 4), round(c, 2)],
                          "tip": (f"<b>{monitor} · {scale}</b><br>{batch}<br>audit {f:.2f}% of honest"
                                  f"<br>catch {c:.1f}% of backdoors")} for f, c in r["points"]],
                **({"markLine": FIVE} if first else {}),
            })
            first = False
            rows += [{"monitor": monitor, "batch": batch, "scale": scale, "run": run,
                      "audit_pct": round(f, 4), "caught_pct": round(c, 2)} for f, c in r["points"]]
    return out


def build() -> Figure:
    rows: list = []
    frames = [{"series": series_for(m, rows)} for m in S.SCALE_MONITORS]
    facts = {"son_b2_distinct": S.resolution_curve(
        S.SCALE_RUNS[("Sonnet 5.5 UM", "new 500 (batch 2)")]["0-10"])["distinct_honest"]}
    option = C.base(
        grid={"left": 62, "right": 28, "top": 56, "bottom": 62},
        xAxis=C.axis("Share of honest programs audited (log scale)", **XA),
        yAxis=C.axis("Backdoors caught", gap=46, type="value", min=0, max=100,
                     axisLabel={"formatter": "{value}%"}),
        legend={"top": 0, "left": 56, "data": [NAMES[(s, b)] for b in (0, 1) for s, _ in SCALES]},
        series=frames[0]["series"],
    )
    return Figure(option=option, data=rows, facts=facts,
                  dial={"label": "Monitor", "steps": S.SCALE_MONITORS, "initial": 0, "frames": frames})
