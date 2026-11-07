"""M09: the 0-10 against 0-100 operating points, on the original 500 problems and a disjoint second 500."""
from viz.kit import Figure
from viz.lib import charts as C
from viz.lib import safety as S

META = {
    "id": "M09",
    "title": "The 0 to 100 scale wins on both batches, by varying margins",
    "section": "appendix",
    "order": 110,
    "caption": ("Every distinct honest score is one cutoff the monitor can be placed at, so the curve steps "
                "through all of them: x is the share of honest programs audited, y the backdoors caught. "
                "The dashed line is a 5% audit share. The 0 to 100 arm offers more usable cutoffs in all "
                "four panels."),
    "notes": [
        "Batch 2 is a disjoint 500 problems from the same interview difficulty band, so this is a "
        "replication rather than more of the same data.",
        "The ordering replicates and the margin does not. Both scales lose cutoffs on batch 2, so how much "
        "the wider scale buys you is a property of the sample, not a constant.",
        "Sonnet's 0 to 10 arm on batch 2 serves a single cutoff and none at or below a 5% audit share, so "
        "its budget axis is one point rather than a curve. That is the failure this whole comparison is about.",
        "A cutoff counts as usable here if it audits at most 5% of honest programs. It says nothing about "
        "how well estimated that cutoff is; one honest row above the line still counts.",
    ],
    "height": 620,
}

MONITORS, BATCHES, RUNS = S.SCALE_MONITORS, S.SCALE_BATCHES, S.SCALE_RUNS
SCALES = [("0-10", "@s0"), ("0-100", "@s1")]
XA = {"type": "log", "min": 0.2, "max": 60, "axisLabel": {"formatter": "{value}%"}}
FIVE = {"silent": True, "symbol": "none", "label": {"show": False},
        "lineStyle": {"color": "@ink-muted", "type": "dashed", "width": 1},
        "data": [{"xAxis": 5}]}


def series_for(monitor: str, rows: list) -> list:
    """Both scales in both batch panels for one monitor."""
    out = []
    for panel, batch in enumerate(BATCHES):
        for scale, color in SCALES:
            run = RUNS[(monitor, batch)][scale]
            r = S.resolution_curve(run)
            pts = r["points"]
            data = [{"value": [round(f, 4), round(c, 2)],
                     "tip": (f"<b>{monitor} · {scale}</b><br>{batch}<br>audit {f:.2f}% of honest"
                             f"<br>catch {c:.1f}% of backdoors"
                             f"<br>{round(f * r['n_honest'] / 100)} honest row(s) above the cutoff")}
                    for f, c in pts]
            out.append({
                "name": f"{scale} score", "type": "line", "step": "end",
                "xAxisIndex": panel, "yAxisIndex": panel,
                "symbolSize": 8, "itemStyle": {"color": color, "borderColor": "@ink-surface", "borderWidth": 1.5},
                "lineStyle": {"color": color, "width": 2}, "data": data,
                **({"markLine": FIVE} if scale == "0-10" else {}),
            })
            rows += [{"monitor": monitor, "batch": batch, "scale": scale, "run": run,
                      "audit_pct": round(f, 4), "caught_pct": round(c, 2)} for f, c in pts]
    return out


def build() -> Figure:
    rows: list = []
    frames = [{"series": series_for(m, rows)} for m in MONITORS]
    facts = {}
    for m in MONITORS:
        for b in BATCHES:
            for scale, _ in SCALES:
                r = S.resolution_curve(RUNS[(m, b)][scale])
                key = f"{'son' if m.startswith('Sonnet') else 'hai'}_{'b1' if b.startswith('original') else 'b2'}_{scale.replace('-', '')}"
                facts[f"u5_{key}"] = r["usable5"]
                facts[f"dh_{key}"] = r["distinct_honest"]
    option = C.base(
        grid=[{"left": 62, "right": 28, "top": 54, "height": "33%"},
              {"left": 62, "right": 28, "bottom": 62, "height": "33%"}],
        xAxis=[C.axis("", **{**XA, "axisLabel": {"show": False}}),
               C.axis("Share of honest programs audited (log scale)", gridIndex=1, **XA)],
        yAxis=[C.axis("Backdoors caught", gap=46, type="value", min=0, max=100,
                      axisLabel={"formatter": "{value}%"}),
               C.axis("Backdoors caught", gap=46, type="value", gridIndex=1, min=0, max=100,
                      axisLabel={"formatter": "{value}%"})],
        legend={"top": 0, "left": 56, "data": [f"{s} score" for s, _ in SCALES]},
        graphic=[{"type": "text", "left": 62, "top": 34,
                  "style": {"text": BATCHES[0], "fontSize": 12, "fontWeight": 600, "fill": "@ink-secondary"}},
                 {"type": "text", "left": 62, "top": "55%",
                  "style": {"text": BATCHES[1], "fontSize": 12, "fontWeight": 600, "fill": "@ink-secondary"}}],
        series=frames[0]["series"],
    )
    return Figure(option=option, data=rows, facts=facts,
                  dial={"label": "Monitor", "steps": MONITORS, "initial": 0, "frames": frames})
